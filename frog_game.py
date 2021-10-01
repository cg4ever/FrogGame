# from _typeshed import Self
import numpy as np
import pygame
import os
import random
import time
from collections import defaultdict
import itertools
import matplotlib.pyplot as plt
import pickle

from pygame.locals import *

sourceFileDir = os.path.dirname(os.path.abspath(__file__))
os.chdir(sourceFileDir)


# choose game speed or change clock to False for game without buffer
game_speed = 30 # ab 40 wird das Spiel erst ziemlich anspruchsvoll ;)
clock = True

testing = False
testnumbers = []


pygame.init()
pygame.mixer.init()

pygame.display.set_caption("Frog Game")

pygame.font.init()
num_fly_font = pygame.font.SysFont('Calibri', 13)
num_fly_surface = num_fly_font.render('Number of flies left: ', False, (255, 100, 0))
game_over_font = pygame.font.SysFont('Calibri', 45)
game_over_surface = game_over_font.render('GAME OVER', False, (255, 100, 0))
try_again_font = pygame.font.SysFont('Calibri', 35)
try_again_surface = try_again_font.render('Click Return and go to the next level', False, (255, 100, 0))
winner_font = pygame.font.SysFont('Calibri', 45)
description_font1 = pygame.font.SysFont('Calibri', 13)
description_surface1 = description_font1.render('Press one of the arrow keys to catch a fly, press spacebar to dive under water and escape from the stork. But watch out, you can only take one action at a time and each costs you energy.', False, (255,100,0))
description_font2 = pygame.font.SysFont('Calibri', 13)
description_surface2 = description_font2.render('Fortunately eating flies gives you energy - the goal is to catch them all. If you lose a live, just press the return key to start again!', False, (255,100,0))


# defining constants, colors, sounds, images
tonguelength = 11
tongue_velocity = 5
permeability = 1 # value between 0 and 10 - higher values make frog more visible when under water
frog_period = 120 # after how many time steps a frog changes its direction
stork_period = 81

directions = {'left': np.array([0,-1]), 'right': np.array([0,1]), 'up': np.array([-1,0]), 'down': np.array([1,0])}  # , 'northeast':np.array([-1,1]), 'northwest':np.array([-1,-1]), 'southeast': np.array([1,-1]), 'southwest': np.array([1,1])
directions2 = {'right': np.array([0,1]), 'up': np.array([-1,0]), 'down':np.array([1,0])} # three directions for new flies after reproduction

health = 30

black = (0,0,0)
white = (255, 255, 255)
grey = (210, 210, 210)
green = (0, 255, 0)
red = (255, 0, 0)
dark_red = (120, 0, 0)
light_red = (255, 110, 110)
water_blue = (156, 211, 219)
light_green = (160, 255, 160)

slurpSound = pygame.mixer.Sound("sounds/slurp.wav")
splashSound = pygame.mixer.Sound("sounds/splash.wav") # Music used from https://www.FesliyanStudios.com
gameoverSound = pygame.mixer.Sound("sounds/mixkit-retro-arcade-game-over-470.wav")
winnerSound = pygame.mixer.Sound("sounds/mixkit-game-level-completed-2059.wav")

full_image = pygame.image.load("graphics/full.png") # image of a full heart
full_image.set_alpha(128) # make image transparent
full_image = pygame.transform.smoothscale(full_image, (45,40)) # scale image
empty_image = pygame.image.load("graphics/empty.png") # image of an empty heart
empty_image.set_alpha(128)
empty_image = pygame.transform.smoothscale(empty_image, (45,40))

# values for grid and making the screen
cell_size = 4
rows = 125
cols = 210

grid_width = cell_size * cols 
grid_height = cell_size * rows

window_size = [int(grid_width) + 150, int(grid_height) + 95]
screen = pygame.display.set_mode(window_size)



# fills a cell with flies into three directions after reproduction
def fillCellWithFlies():
    return [Fly(dir) for dir in directions2.values()]

def randomNewDirection():
    dirs = ['left', 'right', 'up', 'down']
    return directions[dirs[random.randint(0,3)]]

# computes difference in two values (for example x-coordinates) considering the periodic behavior of the game
def diff(a,b, length):
    return min(length+a-b, length+b-a, abs(a-b))


class Stork:
    def __init__(self, part, direction):
        self.part = part # different parts of the stork will be colored in different ways 
        self.direction = np.array(direction)

        if part == 'invisible': # we don't want the stork to behave too "edgy", so we add some extra invisible cells to make it smooth
            self.color = water_blue 
        elif part in ('outer', 'black'):
            self.color = black
        elif part == 'white':
            self.color = white
        elif part == 'shaded':
            self.color = grey
        elif part == 'darksnabel':
            self.color = red
        elif part == 'lightsnabel':
            self.color = light_red
        


class Frog:
    def __init__(self, part, direction, tonguestate = 0, uppertongue = False, originaltongue = False):
        self.part = part
        if part == 'invisible':
            self.color = water_blue
        elif part == 'body':
            self.color = green
        elif part == 'outer':
            self.color = black
        elif part == 'inner':
            self.color = black
        elif part == 'white':
            self.color = white
        elif part == 'tongue':
            self.color = red
            self.tonguestate = tonguestate # integer that indicates after how many steps this part of the tongue will disappear
            self.uppertongue = uppertongue # bool that indicates if this part of the tongue is the upper part
            self.originaltongue = originaltongue # bool that is True iff part of the tongue is the frogs continual mouth
        self.direction = np.array(direction)


class Fly:
    def __init__(self, direction):
        self.color = black
        self.direction = np.array(direction)
    
    # change direction of a fly by 180 degrees
    def changeDirection(self):
        self.direction = -self.direction


class Grid:
    def __init__(self):
        self.storks = defaultdict(list)
        self.frogs = defaultdict(list)
        self.flies = defaultdict(list)

    def appendStork(self, Stork, row, col):
        self.storks[(row, col)].append(Stork)
        
    def appendFrog(self, Frog, row, col):
        self.frogs[(row,col)].append(Frog)

    def appendFly(self, Fly, row, col):
        self.flies[(row, col)].append(Fly)


class CellularAutomaton:
    def __init__(self, health = 0, under_water = False, level = 1):
        self.level = level
        self.under_water = under_water
        self.lives = 3
        self.health = health
        self.health_displayed = health
        self.numflies = 0
        self.storks = defaultdict(list)
        self.frogs = defaultdict(list)
        self.flies = defaultdict(list)
        self.paused = False
        self.game_over = False
        self.winner = False
        self.caught_flies = 0
        self.reproducing = True
        self.under_water_time = 75
        self.collisions = 0

    # draws the three hearts (full or empty) according to the player's lives
    def drawHearts(self):
        if self.lives >= 1:
            screen.blit(full_image, (20,20))
        else:
            screen.blit(empty_image, (20,20))
        if self.lives >= 2:
            screen.blit(full_image, (70,20))
        else:
            screen.blit(empty_image, (70,20))
        if self.lives == 3:
            screen.blit(full_image, (120,20))
        else:
            screen.blit(empty_image, (120,20))

    # draws the colored life-bar of the player's health and the current health state
    def drawLife(self):
        for i in range(100):
            color = ( i*240/100, 255, i*240/100) # for i = 0 we get green, for increasing i the color tends to be more white
            my_bar = pygame.Surface((15,2)) # each bar has a height of 2 units
            my_bar.set_alpha(198)
            my_bar.fill(color)
            screen.blit(my_bar, (window_size[0]-180, 20+2*i)) # each bar is displayed units lower than previous
        # the following assures that the black current-health-bar doesn't 'jump' but moves smoothly, when the health changes
        if self.health_displayed < self.health:
            self.health_displayed = min(self.health, self.health_displayed + 1)
        elif self.health_displayed > self.health:
            self.health_displayed = max(self.health, self.health_displayed - 1)
        pygame.draw.rect(screen, black, [window_size[0]-180, 20+2*int(100- self.health_displayed), 15, 2])
        
    def drawFlyStanding(self):
        # draw black square indicating a fly
        my_fly = pygame.Surface((15,15))
        my_fly.set_alpha(198)
        my_fly.fill(black)
        screen.blit(my_fly, (window_size[0]-205, window_size[1]-120))
        
        # draw the number of flies (numflies) left
        flycountfont = pygame.font.SysFont('Calibri', 15)
        flycountsurface = flycountfont.render('x ' + str(self.numflies), False, black) 
        flycountsurface.set_alpha(180)
        screen.blit(flycountsurface, (window_size[0]-185, window_size[1]-120))  
        
    def writeDescription(self):
        screen.blit(description_surface1, (10,window_size[1]-50))   
        screen.blit(description_surface2, (10,window_size[1]-25)) 
        levelfont = pygame.font.SysFont('Calibri', 15)
        levelsurface = levelfont.render('Level '+str(self.level), False, (255, 100, 0)) 
        screen.blit(levelsurface, (window_size[0]-100, window_size[1]-200)) 

    def getFrogCenter(self):
        for pos, list in self.frogs.items():
            for frog in list:
                if frog.part == 'tongue' and frog.originaltongue:
                    return pos

    def hasToEvade(self, safety_distance):
        return self.computeFrogStorkDistance() < safety_distance and self.health >= 6

    # checks for a given fly if there is a stork in the next cell that is 'crashing' the fly frontally 
    def flyHasToBounceFromStork(self, fly, row, col):
        if ((row+fly.direction[0])%rows, (col+fly.direction[1])%cols) in self.storks.keys(): # checks if there is any stork in the next cell
            for stork in self.storks[((row+fly.direction[0])%rows, (col+fly.direction[1])%cols)]: # checks every stork in the next cell
                if all(stork.direction == -fly.direction): # checks if stork has opposite direction as fly
                    return True
        return False
    
    # same as above but checks for stork OR frog
    def flyHasToBounce(self, fly, row, col):
        if ((row+fly.direction[0])%rows, (col+fly.direction[1])%cols) in self.storks.keys():
            for stork in self.storks[((row+fly.direction[0])%rows, (col+fly.direction[1])%cols)]:
                if all(stork.direction == -fly.direction):
                    return True
        if ((row+fly.direction[0])%rows, (col+fly.direction[1])%cols) in self.frogs.keys():
            for frog in self.frogs[((row+fly.direction[0])%rows, (col+fly.direction[1])%cols)]:
                if all(frog.direction == -fly.direction):
                    return True
        return False

    # checks for a given fly if it has to turn around according to the game's rules (two cases)
    def flyHasToTurnFromStork(self, fly, row, col):
        if ((row+2*fly.direction[0])%rows, (col+2*fly.direction[1])%cols) in self.storks.keys(): # checks if there is a stork in the cell after next
            for stork in self.storks[((row+2*fly.direction[0])%rows, (col+2*fly.direction[1])%cols)]:
                if all(stork.direction == -fly.direction): # checks if stork has opposite direction as fly
                    return True
        if ((row+fly.direction[0])%rows, (col+fly.direction[1])%cols) in self.storks.keys(): # checks if there is a stork in the next cell
            for stork in self.storks[((row+fly.direction[0])%rows, (col+fly.direction[1])%cols)]:
                if stork.direction@fly.direction == 0: # checks if stork has direction perpendicular to fly's direction
                    return True
        return False

    # same as above but checks for stork OR frog
    def flyHasToTurn(self, fly, row, col):
        if ((row+2*fly.direction[0])%rows, (col+2*fly.direction[1])%cols) in self.storks.keys():
            for stork in self.storks[((row+2*fly.direction[0])%rows, (col+2*fly.direction[1])%cols)]:
                if all(stork.direction == -fly.direction):
                    return True
        if ((row+fly.direction[0])%rows, (col+fly.direction[1])%cols) in self.storks.keys():
            for stork in self.storks[((row+fly.direction[0])%rows, (col+fly.direction[1])%cols)]:
                if stork.direction@fly.direction == 0:
                    return True
        if ((row+2*fly.direction[0])%rows, (col+2*fly.direction[1])%cols) in self.frogs.keys():
            for frog in self.frogs[((row+2*fly.direction[0])%rows, (col+2*fly.direction[1])%cols)]:
                if all(frog.direction == -fly.direction):
                    return True
        if ((row+fly.direction[0])%rows, (col+fly.direction[1])%cols) in self.frogs.keys():
            for frog in self.frogs[((row+fly.direction[0])%rows, (col+fly.direction[1])%cols)]:
                if frog.direction@fly.direction == 0:
                    return True
        return False

    # checks for a flies new position (row, col), if this cell will be occupied by an incoming stork
    def flyWillBeCrashedByStork(self, row, col):
        for dir in directions.values(): 
            # checks for example for dir = np.array([0,1]) if there is a stork moving right in the left neighbor cell (into the cell (row, col))
            if ((row-dir[0])%rows, (col-dir[1])%cols) in self.storks.keys():
                for stork in self.storks[((row-dir[0])%rows, (col-dir[1])%cols)]:
                    if all(stork.direction == dir):
                        return True
        return False

    # same as above but checks for stork OR frog
    def flyWillBeCrashed(self, row, col):
        for dir in directions.values():
            if ((row-dir[0])%rows, (col-dir[1])%cols) in self.storks.keys():
                for stork in self.storks[((row-dir[0])%rows, (col-dir[1])%cols)]:
                    if all(stork.direction == dir):
                        return True
            if ((row-dir[0])%rows, (col-dir[1])%cols) in self.frogs.keys():
                for frog in self.frogs[((row-dir[0])%rows, (col-dir[1])%cols)]:
                    if all(frog.direction == dir):
                        return True
        return False

    # checks if a given fly in a given cell will be caught by a tongue
    def flyGetsCaught(self, fly, row, col):
        # checks if there is a tongue in the current cell
        if (row, col) in self.frogs.keys():
            for frog in self.frogs[(row, col)]:
                if frog.part == 'tongue':
                    return True
        # checks if there is a tongue in the next cell
        if ((row+fly.direction[0])%rows, (col+fly.direction[1])%cols) in self.frogs.keys():
            for frog in self.frogs[((row+fly.direction[0])%rows, (col+fly.direction[1])%cols)]:
                if frog.part == 'tongue':
                    return True
        # checks if there is a tongue in the cell after next, that is moving towards the fly
        if ((row+2*fly.direction[0])%rows, (col+2*fly.direction[1])%cols) in self.frogs.keys():
            for frog in self.frogs[((row+2*fly.direction[0])%rows, (col+2*fly.direction[1])%cols)]:
                if frog.part == 'tongue' and all(frog.direction == -fly.direction):
                    return True
        return False


    def appendStork(self, Stork, row, col):
        self.storks[(row, col)].append(Stork)
        
    def appendFrog(self, Frog, row, col):
        self.frogs[(row,col)].append(Frog)

    def appendFly(self, Fly, row, col):
        self.flies[(row, col)].append(Fly)
        self.numflies += 1

    # returns a new defaultdict containing the new storks under no additional rules
    def updateStorks(self):
        updated = Grid()
        for (row, col), cell in self.storks.items():
            for stork in cell:
                updated.appendStork(stork, (row+stork.direction[0])%rows, (col+stork.direction[1])%cols) # stork moves into the next cell
                # pause the game if a stork and a frog have been in the same cell -> collision 
                if (row, col) in self.frogs.keys():
                    if not self.paused:              
                        self.paused = True
                        pygame.mixer.Sound.play(gameoverSound)
        return updated.storks

    # same as above
    def updateFrogs(self):
        updated = Grid()
        for (row, col), cell in self.frogs.items():
            for frog in cell:
                updated.appendFrog(frog, (row+frog.direction[0])%rows, (col+frog.direction[1])%cols) # frog moves into the next cell
        return updated.frogs

    # same as above
    def updateFlies(self):
        updated = Grid()
        for (row, col), cell in self.flies.items():
            for fly in cell:
                # for each fly first the new direction and the new position is determined
                if self.flyHasToBounce(fly, row, col):
                    fly.changeDirection()
                    new_row = (row+fly.direction[0])%rows
                    new_col = (col+fly.direction[1])%cols
                elif self.flyHasToTurn(fly, row, col):
                    fly.changeDirection()
                    new_row = row
                    new_col = col
                else:
                    new_row = (row+fly.direction[0])%rows
                    new_col = (col+fly.direction[1])%cols
    
                # if the fly's new position will be occupied (crashed), this fly is eliminated and the number of flies reduces by 1
                if self.flyWillBeCrashed(new_row, new_col):
                    self.numflies -= 1
                    if self.numflies == 0:
                        self.winner = True
                        pygame.mixer.Sound.play(winnerSound)
                    continue
                # else the fly can just move into the next cell 
                else:
                    updated.appendFly(fly, new_row, new_col)
        # in level two the flies are reproducing (two flies in one cell create one new fly) until the number of flies reaches 60 and the player loses a life
        if self.level >= 2 and self.reproducing:
            for position, cell in updated.flies.items():
                if len(cell) == 2:
                    updated.flies[position] = fillCellWithFlies() # fillCellWithFlies() returns a list of three flies
                    self.numflies += 1
                    if self.numflies > 60 and not self.paused:
                        self.reproducing = False
                        pygame.mixer.Sound.play(gameoverSound)
                        self.paused = True
        return updated.flies

    # update the defaultdicts when there are no additional rules
    def update(self):
        storks = self.updateStorks()
        flies = self.updateFlies()
        if not self.paused:
            self.frogs = self.updateFrogs()
            self.flies = flies
            self.storks = storks
        else:
            if not testing:
                self.lives -= 1
            else: 
                self.lives -= 1
                self.collisions += 1

    # returns a new defaultdict containing the new frogs when the tongue is activated (into a certain direction dir)
    def updateTongueFrogs(self, dir):
        updated = Grid()
        for (row, col), cell in self.frogs.items():
            for frog in cell:
                if frog.part == 'tongue':
                    # if the tonguestate of a regular tongue goes below 0, this part of the tongue should just disappear
                    if frog.tonguestate <= 0 and not frog.originaltongue:
                        continue 
                    # else the tonguestate is reduced by one every timestep
                    # but the upper part of the tongue creates a new section of the tongue before that
                    else:
                        if frog.uppertongue == True:
                            for i in range(1,tongue_velocity):
                                updated.appendFrog(Frog('tongue', frog.direction, tonguestate=frog.tonguestate-2, uppertongue=False), (row + frog.direction[0] + i*dir[0]) % rows, (col + frog.direction[1] + i*dir[1]) % cols) # create almost all of the new section of tongue but the end
                            updated.appendFrog(Frog('tongue', frog.direction, tonguestate=frog.tonguestate-2, uppertongue=True), (row + frog.direction[0] + tongue_velocity*dir[0]) % rows, (col + frog.direction[1] + tongue_velocity*dir[1]) % cols) # create the end of the new section which is now the new uppertongue
                            frog.uppertongue = False # after creating a new part, the uppertongue loses this status
                        frog.tonguestate -= 1                
                updated.appendFrog(frog, (row+frog.direction[0])%rows, (col+frog.direction[1])%cols) # the already existing (and not tongue with tonguestate <= 0) parts of the frog move into the next cell
        return updated.frogs

    # almost the same as updateFlies but also checks if each fly is caught by the tongue
    def updateTongueFlies(self):
        updated = Grid()
        for (row, col), cell in self.flies.items():
            for fly in cell:
                if self.flyGetsCaught(fly, row, col):
                    self.health = min(100, self.health + 10) # each caught fly gives a boost of 10 points but health can only reach a max of 100
                    self.numflies -=1
                    self.caught_flies += 1
                    if self.numflies == 0:
                        self.winner = True
                        pygame.mixer.Sound.play(winnerSound)
                    continue
                elif self.flyHasToBounce(fly, row, col):
                    fly.changeDirection()
                    new_row = (row+fly.direction[0])%rows
                    new_col = (col+fly.direction[1])%cols
                elif self.flyHasToTurn(fly, row, col):
                    fly.changeDirection()
                    new_row = row
                    new_col = col
                else:
                    new_row = (row+fly.direction[0])%rows
                    new_col = (col+fly.direction[1])%cols
    
                if self.flyWillBeCrashed(new_row, new_col):
                    self.numflies -= 1
                    if self.numflies == 0:
                        self.winner = True
                        pygame.mixer.Sound.play(winnerSound)
                    continue
                else:
                    updated.appendFly(fly, new_row, new_col)
        if self.level >= 2:
            if self.reproducing:
                for position, cell in updated.flies.items():
                    if len(cell) == 2:
                        updated.flies[position] = fillCellWithFlies()
                        self.numflies += 1
                        if self.numflies > 60 and not self.paused:
                            self.reproducing = False
                            pygame.mixer.Sound.play(gameoverSound)
                            self.paused = True
        return updated.flies

    # update the defaultdicts when the tongue is activated (into a certain direction dir)
    def updateTongue(self, dir):
        storks = self.updateStorks()
        flies = self.updateTongueFlies()
        if not self.paused:
            self.frogs = self.updateTongueFrogs(dir)
            self.flies = flies
            self.storks = storks
        else:
            if not testing:
                self.lives -= 1
            else: 
                self.lives -= 1
                self.collisions += 1


    # returns a new defaultdict containing the new storks when the frog is under water (no collisions possible anymore)
    def updateUnderWaterStorks(self):
        updated = Grid()
        for (row, col), cell in self.storks.items():
            for stork in cell:
                updated.appendStork(stork, (row+stork.direction[0])%rows, (col+stork.direction[1])%cols)
        return updated.storks

    # almost same as updateFlies, but flies can only bounce, turn and crash with storks
    def updateUnderWaterFlies(self):
        updated = Grid()
        for (row, col), cell in self.flies.items():
            for fly in cell:
                if self.flyHasToBounceFromStork(fly, row, col):
                    fly.changeDirection()
                    new_row = (row+fly.direction[0])%rows
                    new_col = (col+fly.direction[1])%cols
                elif self.flyHasToTurnFromStork(fly, row, col):
                    fly.changeDirection()
                    new_row = row
                    new_col = col
                else:
                    new_row = (row+fly.direction[0])%rows
                    new_col = (col+fly.direction[1])%cols
    
                if self.flyWillBeCrashedByStork(new_row, new_col):
                    self.numflies -= 1
                    if self.numflies == 0:
                        self.winner = True
                        pygame.mixer.Sound.play(winnerSound)
                    continue
                else:
                    updated.appendFly(fly, new_row, new_col)
        if self.level >= 2:
            if self.reproducing:
                for position, cell in updated.flies.items():
                    if len(cell) == 2:
                        updated.flies[position] = fillCellWithFlies()
                        self.numflies += 1
                        if self.numflies > 60 and not self.paused:
                            self.reproducing = False
                            pygame.mixer.Sound.play(gameoverSound)
                            self.paused = True
        return updated.flies

    # update the defaultdicts when the frog is under water
    def updateUnderWater(self):
        flies = self.updateUnderWaterFlies()
        if not self.paused:
            frogs = self.updateFrogs()
            self.storks = self.updateUnderWaterStorks()
            self.frogs = frogs
            self.flies = flies
        else: 
            if not testing:
                self.lives -= 1
            else: 
                self.lives -= 1
                self.collisions += 1

    # will be used for the random changes of direction
    def changeFrogsDirection(self, direction):
        for cell in self.frogs.values():
            for frog in cell:
                frog.direction = direction

    # will be used for the random changes of direction
    def changeStorksDirection(self, direction):
        for cell in self.storks.values():
            for stork in cell:
                stork.direction = direction

    # reset the initial values of the original tongue - otherwise it would be 'eliminated' in the function updateTongueFrogs
    def reviveOriginalTongues(self):
        for cell in self.frogs.values():
            for frog in cell:
                if frog.part == 'tongue' and frog.originaltongue:                          
                    frog.tonguestate =2*tonguelength
                    frog.uppertongue = True

    def draw(self):
        screen.fill(black)
        if not self.game_over and not self.winner:
            pygame.draw.rect(screen, water_blue, [0, 0, grid_width, grid_height])

            for (row, col), cell in self.frogs.items(): # draw frogs
                for frog in cell:
                    color = frog.color
                    if color == red: # this distinction is made, because there could be a frog's tongue and a frog's body in the same cell, but we only want the tongue (red) to be drawn
                        if self.under_water:
                            color = (156*(10-permeability)/10 + color[0]*permeability/10, 211*(10-permeability)/10 + color[1]*permeability/10, 219*(10-permeability)/10 + color[2]*permeability/10) # make the frog 'shine through' the water surface
                        pygame.draw.rect(screen, color, [cell_size * col , cell_size * row, cell_size, cell_size])
                        break
                    elif color == green:
                        color = ( (100-self.health)*240/100, 255, (100-self.health)*240/100)
                    if self.under_water:
                        color = (156*(10-permeability)/10 + color[0]*permeability/10, 211*(10-permeability)/10 + color[1]*permeability/10, 219*(10-permeability)/10 + color[2]*permeability/10) # make the frog 'shine through' the water surface
                    pygame.draw.rect(screen, color, [cell_size * col, cell_size * row, cell_size, cell_size])

            for (row, col), cell in self.flies.items(): # draw flies
                for fly in cell:
                    color = fly.color
                    pygame.draw.rect(screen, color, [cell_size * col, cell_size * row, cell_size, cell_size])

            for (row, col), cell in self.storks.items(): # draw storks
                for stork in cell:
                    color = stork.color
                    pygame.draw.rect(screen, color, [cell_size * col, cell_size * row, cell_size, cell_size])

            self.drawHearts()
            self.drawLife()
            self.drawFlyStanding()
            self.writeDescription()
        elif self.game_over:
            screen.blit(game_over_surface, (100,100))
            screen.blit(try_again_surface, (100, 200))
        else: 
            winner_surface = winner_font.render('WINNER - Flies caught: '+str(self.caught_flies), False, (255, 100, 0))
            screen.blit(winner_surface, (80,100))
            screen.blit(try_again_surface, (80, 200))          

    # when the player loses a life and restarts the game with a new life
    def startWithNewLife(self):
        self.paused = False
        self.under_water = True
        self.health = max(self.health, 30) # if health is below 30, it should be filled up again
        self.removeTongues() # is necessary if the tongue is activated, when the player loses a life


    def removeTongues(self):
        to_delete = []
        for (row, col), cell in self.frogs.items():
            for frog in cell:
                if frog.part == 'tongue' and not frog.originaltongue:
                    cell.remove(frog)
                    if not cell: # if there is no frog left in the list, we want to delete the cell's key from the defaultdict
                        to_delete.append((row, col))
        for key in to_delete:
            del self.frogs[key]
        self.reviveOriginalTongues()

    # when the player has lost all lives or has won the game, a new round can be started
    def startNewRound(self):
        global counter1, counter2, t
        if self.winner: # continue to next level 
            self.level += 1
        if self.game_over: # start again at level one and with three new lives
            self.level = 1
            self.lives = 3
        # reset all variables
        self.game_over = False
        self.winner = False
        self.reproducing = True
        self.health = 30
        self.numflies = 0
        self.caught_flies = 0
        self.storks = defaultdict(list)
        self.frogs = defaultdict(list)
        self.flies = defaultdict(list)
        self.paused = False
        self.under_water = False
        self.makeLevelOne()
        counter1 = 0
        counter2 = 0
        t = 0

    # create a new frog with different parts so that it looks beautiful on the screen, (row, col) is the center of the frog's body (the tongue/ mouth)
    def createFrog(self, direction, row, col):
        outer = [ [-6,0], [7,0], [-6,1], [7,1], [-7,2], [6,2], [-8,3], [7,3], [-8,4], [6,4], [-8,5], [7,5], [3,5], [-7,6], [7,6], [-3,6], [2,6], [4,6], [-6,7], [-5,7], [-4,7], [-2,7], [1,7], [4,7], [7,7], [-1,8], [0,8], [5,8], [6,8]]
        white = [ [4,0], [5,0], [6,0], [5,1], [6,1], [-6,2], [-5,2], [-4,2], [-7,3], [-6,3], [-5,3], [-4,3], [-3,3], [-7,4], [-4,4], [-3,4], [-7,5], [-4,5], [-3,5], [-6,6], [-5,6], [-4,6]]
        inner = [ [0,1], [0,2], [0,3], [0,4], [2,4], [-6,4], [-5,4], [-1,5], [2,5], [-6,5], [-5,5], [5,6] ]
        body = [ [i, 0] for i in range(-5, 4) if i != 0 ] + [ [i, 1] for i in range(-5, 5) if i != 0 ] + [ [i, 2] for i in range(-3, 6) if i != 0 ] + [ [i, 3] for i in range(-2, 7) if i != 0 ] + [ [i, 4] for i in range(-2, 6) if i != 0 and i != 2] + [ [-2,5], [0,5], [1,5], [4,5], [5,5], [6,5], [-2,6], [-1,6], [0,6], [1,6], [6,6], [-1,7], [0,7], [5,7], [6,7]]
        invisible = [ [7,2], [7,4], [3,6], [3,7], [2,7], [-3,7], [-7,0], [-7,1] ]
        cells = {'outer': outer, 'white': white, 'inner': inner, 'body': body, 'invisible': invisible}
        for type in cells:
            for cell in cells[type]:
                self.appendFrog(Frog(type, direction), row+cell[0], col+cell[1])
                if cell[1] != 0:
                    self.appendFrog(Frog(type, direction), row+cell[0], col-cell[1])
        self.appendFrog(Frog('tongue', direction, tonguestate = 2*tonguelength, uppertongue = True, originaltongue=True), row, col)
        self.frog_center = np.array([row, col])

    # similar to createFrog
    def createStork(self, direction, row, col):
        outer = [ [0,0], [0,1], [0,2], [-1,1], [-2,2], [-3,3], [-3,4], [-4,5], [-4,6], [-4,7], [-4,8], [-4,9], [-4,10], [-4,11], [-3,12], [-4,13], [-5,13],[-6,12], [-7,11], [-8,11], [-9,11], [-10, 12], [-11,13], [-11,14], [-11,15], [-10,16], [-9,17], [-9,18], [-9,19], [-9,20], [-9,21], [-8,22], [-8,23], [-7,24], [-6,24], [-6,23], [-6,22], [-6,21], [-6,20], [-6,19], [-5,17], [-5,16], [-4,15], [-3,15], [-2,15], [-1,14], [0,14], [1,13], [2,12], [2,11], [3,10], [4,10], [5,10], [6,10], [7,10], [8,9], [7,9], [6,8], [7,7], [6,7], [5,6], [6,5], [5,5], [4,4], [3,4], [2,4], [1,3] ]
        white = [ [-2,4], [-2,5], [-3,5], [-3,6]] + [[i,j] for i in range(-3,3) for j in range(7,10)] + [[-2,10], [-3,10], [-1,11], [-2,11], [-3,11], [-1,12], [-2,12], [-2,13], [-3,13]] + [[i,14] for i in range(-10, -2)] + [[-7,13], [-8,13], [-9,13], [-7,15], [-9,15], [-10,15], [-8,16], [-9, 16]]
        shaded = [ [-1,2], [0,3], [-1,3], [-2,3], [0,4], [-1,4], [3,5], [2,5], [1,5], [2,6], [1,6], [0,6], [-1,6], [4,7], [3,7], [3,8], [5,9], [4,9], [3,9], [1,11], [0,11], [1,12], [0,12], [0,13], [-1,13], [-2,14], [-6,13], [-7,12], [-8,12], [-9,12], [-10,13]]
        black = [[-8, 15], [1,4], [0,5], [-1,5], [-2,6], [4,5], [4,6], [3,6], [5,7], [5,8], [4,8], [6,9], [2,10], [1,10], [0,10], [-1,10], [-5,15], [-6,15], [-6,18]]
        dark_snabel = [ [-6,16], [-7,16], [-6,17]]
        light_snabel = [[i, j] for i in range(-8, -6) for j in range(17,22)] + [ [-7,22], [-7,23]]
        invisible = [[-4,12], [-5,12], [-5,11], [-6,11], [-5,10], [-6,10], [-5,9], [-4,16], [3,11], [7,8], [6,6], [2,3], [1,2]]

        cells = {'outer': outer, 'white': white, 'shaded': shaded, 'black': black, 'darksnabel': dark_snabel, 'lightsnabel': light_snabel, 'invisible': invisible}
        for type in cells:
            for cell in cells[type]:
                self.appendStork(Stork(type, direction), row+cell[0], col+cell[1])

    def getOuterFrogs(self):
        positions = []
        for pos, list in self.frogs.items():
            for frog in list:
                if frog.part == 'outer':
                    positions.append(pos)
        return positions

    def getOuterStorks(self):
        positions = []
        for pos, list in self.storks.items():
            for stork in list:
                if stork.part == 'outer':
                    positions.append(pos)
        return positions


    def computeFrogStorkDistance(self):
        min_dist = 1000
        frog_center = self.getFrogCenter()
        stork_outer_positions = self.getOuterStorks()
        for stork_pos in stork_outer_positions:
            x = diff(frog_center[1], stork_pos[1], cols)
            y = diff(frog_center[0], stork_pos[0], rows)
            min_dist = min(min_dist,max(x,y))
        return min_dist - 8 # the frog center has a distance of 8 to its outer parts

    def makeLevelOne(self):
        self.createFrog([-1, 0], 62, 120)
        self.createStork([1,0], 100,70)

        start_flies = 40
        for i in range(start_flies):
            dir = randomNewDirection()
            row = random.randint(0, rows-1)
            col = random.randint(0, cols-1)
            self.appendFly(Fly(dir), row, col)

#######################################################################################
#######################################################################################
#######################################################################################

# main starts here



def stepsNeeded(pf, ps, runs, drawing = False):
    ts = []
    wins = 0
    for i in range(runs):
        CA = CellularAutomaton(health = 30, level = 1)
        CA.makeLevelOne()
        
        clock2 = pygame.time.Clock()

        t = 0
        running = True
        counter1 = 0 # counter for tongue
        counter2 = 0 # counter for under water

        while running: 
            events = pygame.event.get()
            for event in events:
                if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE): # game ends and pygame window is closed
                    running = False

            if not CA.paused and not CA.game_over and not CA.winner: # game is running and is updated every timestep
                if counter1 == 0 and counter2 == 0: # no additional rules
                    CA.update()            
                    if CA.health < 0:
                        CA.paused = True
                        CA.lives -= 1
                elif counter1 != 0: # tongue is activated
                    CA.updateTongue(dir)
                    if counter1 == 2*tonguelength: # first time step where tongue is activated
                        pygame.mixer.Sound.play(slurpSound)
                    if counter1 == 1: # last time step where the tongue is activated
                        CA.reviveOriginalTongues()
                    counter1 -= 1
                else: # frog is under water
                    if CA.health < 0:
                        CA.paused = True
                        CA.lives -= 1
                    CA.updateUnderWater()
                    if counter2 == CA.under_water_time: # first time step
                        pass
                        pygame.mixer.Sound.play(splashSound)
                    if counter2 == 1: # last time step
                        CA.under_water = False
                    counter2 -= 1

                if t%pf == 0: # frog randomly changes direction
                    frog_new_dir = randomNewDirection()
                    CA.changeFrogsDirection(frog_new_dir)

                if t%ps == 0: # stork randomly changes direction
                    stork_new_dir = randomNewDirection() 
                    CA.changeStorksDirection(stork_new_dir)

                t += 1
            elif not CA.game_over and not CA.winner: # if player has lost one live and game is paused
                if CA.lives <= 0:
                    if not CA.game_over:
                        CA.game_over = True
                else:
                    CA.startWithNewLife()
                    if counter1 != 0:
                        counter1 = 0
                    counter2 = CA.under_water_time                 
            elif not CA.winner: # game over
                running = False
            else: # victory
                CA.winner = False
                CA.numflies = -1
            if drawing:
                CA.draw()
            if clock: 
                clock2.tick(game_speed)

            pygame.display.flip() 

        ts.append(t)
    print(wins, 'wins')

        # print(pf, ps, 'collisions:', CA.collisions/t)
        # print(testnumbers)
        # print(sum(testnumbers)/len(testnumbers))
        # print('Mean time: ', sum(times)/len(times))
    return ts



def collisionsUntilWin(pf, ps, runs, drawing = False):
    collisions = []
    for i in range(runs):
        CA = CellularAutomaton(health = 30, level = 1)
        CA.makeLevelOne()

        clock2 = pygame.time.Clock()

        t = 0
        running = True
        counter1 = 0 # counter for tongue
        counter2 = 0 # counter for under water

        while running: 
            events = pygame.event.get()
            for event in events:
                if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE): # game ends and pygame window is closed
                    running = False

            if not CA.paused and not CA.game_over and not CA.winner: # game is running and is updated every timestep
                if counter1 == 0 and counter2 == 0: # no additional rules
                    CA.update()            
                    if CA.health < 0:
                        CA.paused = True
                        CA.lives -= 1
                elif counter1 != 0: # tongue is activated
                    CA.updateTongue(dir)
                    if counter1 == 2*tonguelength: # first time step where tongue is activated
                        pygame.mixer.Sound.play(slurpSound)
                    if counter1 == 1: # last time step where the tongue is activated
                        CA.reviveOriginalTongues()
                    counter1 -= 1
                else: # frog is under water
                    CA.updateUnderWater()
                    if counter2 == CA.under_water_time: # first time step
                        pass
                        pygame.mixer.Sound.play(splashSound)
                    if counter2 == 1: # last time step
                        CA.under_water = False
                    counter2 -= 1


                if t%pf == 0: # frog randomly changes direction
                    frog_new_dir = randomNewDirection()
                    CA.changeFrogsDirection(frog_new_dir)

                if t%ps == 0: # stork randomly changes direction
                    stork_new_dir = randomNewDirection() 
                    CA.changeStorksDirection(stork_new_dir)

                t += 1

            elif not CA.game_over and not CA.winner: # if player has lost one live and game is paused 
                CA.startWithNewLife()
                if counter1 != 0:
                    counter1 = 0
                counter2 = CA.under_water_time                 
    
            elif not CA.winner: # game over
                CA.game_over = False

            else: # victory
                running = False
            
            if drawing:
                CA.draw()
            
            if clock: 
                clock2.tick(game_speed)

            pygame.display.flip() 
            
        collisions.append(CA.collisions)
    return collisions



def playGame():
    CA = CellularAutomaton(health = 30, level = 1)
    CA.makeLevelOne()

    started = False

    clock1 = pygame.time.Clock()

    # wait for the player to start the game
    while not started:
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and (event.key == K_RETURN or event.key == K_ESCAPE)):
                started = True

        CA.draw()
        clock1.tick(60)

        pygame.display.flip()

    clock2 = pygame.time.Clock()

    t = 0
    running = True
    counter1 = 0 # counter for tongue
    counter2 = 0 # counter for under water
    buttons = {K_UP: [-1, 0], K_DOWN: [1, 0], K_RIGHT: [0, 1], K_LEFT: [0, -1]}
    times = [] # for measuring how long each time step takes

    while running: 
        start = time.time()
        events = pygame.event.get()
        for event in events:
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE): # game ends and pygame window is closed
                running = False

        if not CA.paused and not CA.game_over and not CA.winner: # game is running and is updated every timestep
            for event in events:
                if counter1 == 0 and counter2 == 0 and event.type == KEYDOWN and event.key in (K_UP, K_DOWN, K_RIGHT, K_LEFT, K_SPACE): # player can only take an action if both counters are 0
                    if event.key == K_SPACE: # frog goes under water
                        counter2 = CA.under_water_time
                        CA.health -= 6
                        CA.under_water = True # used in self.draw(), to make frog disappear
                    else:
                        dir = buttons[event.key]
                        counter1 = 2*tonguelength
                        CA.health -= 3
        
            if counter1 == 0 and counter2 == 0: # no additional rules
                CA.update()            
                if CA.health < 0:
                    CA.paused = True
                    CA.lives -= 1
            elif counter1 != 0: # tongue is activated
                CA.updateTongue(dir)
                if counter1 == 2*tonguelength: # first time step where tongue is activated
                    pygame.mixer.Sound.play(slurpSound)
                if counter1 == 1: # last time step where the tongue is activated
                    CA.reviveOriginalTongues()
                counter1 -= 1
            else: # frog is under water
                CA.updateUnderWater()
                if counter2 == CA.under_water_time: # first time step
                    pass
                    pygame.mixer.Sound.play(splashSound)
                if counter2 == 1: # last time step
                    CA.under_water = False
                counter2 -= 1


            if t%frog_period == 0: # frog randomly changes direction
                frog_new_dir = randomNewDirection()
                CA.changeFrogsDirection(frog_new_dir)

            if t%stork_period == 0: # stork randomly changes direction
                stork_new_dir = randomNewDirection() 
                CA.changeStorksDirection(stork_new_dir)

            t += 1

        elif not CA.game_over and not CA.winner: # if player has lost one live and game is paused
            if CA.lives <= 0:
                if not CA.game_over:
                    CA.game_over = True
            else:
                if not testing:
                    for event in events:
                        if event.type == KEYDOWN and event.key == K_RETURN:
                            CA.startWithNewLife()
                            if counter1 != 0:
                                counter1 = 0
                            counter2 = CA.under_water_time
                else: 
                    CA.startWithNewLife()
                    if counter1 != 0:
                        counter1 = 0
                    counter2 = CA.under_water_time                 

        elif not CA.winner: # game over
            if not testing:
                for event in events:
                    if event.type == KEYDOWN and event.key == K_RETURN:
                        CA.startNewRound()
            else:
                running = False

        else: # victory
            if not testing:
                for event in events:
                    if event.type == KEYDOWN and event.key == K_RETURN:
                        CA.startNewRound()
            else:
                testnumbers.append(CA.collisions)
                print(sum(testnumbers)/len(testnumbers))
                CA = CellularAutomaton(health = 30, level = 1)
                CA.makeLevelOne()
                started = True
        
        CA.draw()
        
        if clock: 
            clock2.tick(game_speed)

        pygame.display.flip() 

        end = time.time()
        times.append(end-start)
        # print(times[-1])



def playWithStrategy(strategy, pf, ps, runs, drawing = False):
    acting_times = []
    winning_times = []
    wins = 0
    for i in range(runs):
        CA = CellularAutomaton(health = 30, level = 1)
        CA.makeLevelOne()

        clock2 = pygame.time.Clock()

        t = 0
        running = True
        counter1 = 0 # counter for tongue
        counter2 = 0 # counter for under water

        while running: 
            events = pygame.event.get()
            for event in events:
                if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE): # game ends and pygame window is closed
                    running = False
                    return []

            if not CA.paused and not CA.game_over and not CA.winner: # game is running and is updated every timestep

                if counter1 == 0 and counter2 == 0: # no additional rules
                    CA.update()            
                    if CA.health < 0:
                        CA.paused = True
                        CA.lives -= 1
                    if CA.hasToEvade(strategy):
                        counter2 = CA.under_water_time
                        CA.health -= 6
                        CA.under_water = True # used in self.draw(), to make frog disappear
                elif counter1 != 0: # tongue is activated
                    CA.updateTongue(dir)
                    if counter1 == 2*tonguelength: # first time step where tongue is activated
                        pygame.mixer.Sound.play(slurpSound)
                    if counter1 == 1: # last time step where the tongue is activated
                        CA.reviveOriginalTongues()
                    counter1 -= 1
                else: # frog is under water
                    CA.updateUnderWater()
                    if CA.health < 0:
                        CA.paused = True
                        CA.lives -= 1
                    if counter2 == CA.under_water_time: # first time step
                        pass
                        pygame.mixer.Sound.play(splashSound)
                    if counter2 == 1: # last time step
                        CA.under_water = False
                    counter2 -= 1


                if t%pf == 0: # frog randomly changes direction
                    frog_new_dir = randomNewDirection()
                    CA.changeFrogsDirection(frog_new_dir)

                if t%ps == 0: # stork randomly changes direction
                    stork_new_dir = randomNewDirection() 
                    CA.changeStorksDirection(stork_new_dir)

                t += 1

            elif not CA.game_over and not CA.winner: # if player has lost one live and game is paused
                if CA.lives <= 0:
                    if not CA.game_over:
                        CA.game_over = True
                else:
                    CA.startWithNewLife()
                    if counter1 != 0:
                        counter1 = 0
                    counter2 = CA.under_water_time                 
        
            elif not CA.winner: # game over
                running = False

            else: # victory
                winning_times.append(t)
                wins += 1
                CA.winner = False
                CA.numflies = -1
            
            if drawing:
                CA.draw()
            
            if clock: 
                clock2.tick(game_speed)

            pygame.display.flip() 

        acting_times.append(t)
    return acting_times, winning_times, wins





runs = 500
frog_periods = [50, 75, 100, 125]
stork_periods = [50, 75, 100, 125]
all_colls_dic = {}
all_steps_dic = {}


# def runStrategySimulation(start, end, step, pf, ps, runs):
#     strategy_data = {'at': {}, 'wt': {}, 'w':{}, 'pf':pf, 'ps':ps, 'runs':runs}
#     ident = random.randint(0,10000)
#     for strategy in range(start, end, step):
#         acting_times, winning_times, wins = playWithStrategy(strategy, pf, ps, runs, drawing=False)
#         strategy_data['at'][strategy] = acting_times
#         strategy_data['wt'][strategy] = winning_times
#         strategy_data['w'][strategy] = wins 
#         print('strategy', strategy, 'finished')   
#         with open('Strategy' + str(pf) + ';' + str(ps) + ';' + str(start) + '-' + str(end) + '_' + str(ident), 'wb') as fp:
#             pickle.dump(strategy_data, fp)

# runStrategySimulation(start=1, end=20, step=1, pf=50, ps=75, runs=500)


# for pf, ps in itertools.product(frog_periods, stork_periods):
#     steps = stepsNeeded(pf, ps, runs, False)
#     all_steps_dic[(pf, ps)] = steps
#     print(pf, ps, 'average steps:', sum(steps)/runs)
# with open('Steps' + str(frog_periods) + str(stork_periods) + str(random.randint(0,10000)) + ', runs= ' + str(runs), 'wb') as fp:
#     pickle.dump(all_steps_dic, fp)


# for pf, ps in itertools.product(frog_periods, stork_periods):
#     colls = collisionsUntilWin(pf, ps, runs, False)
#     all_colls_dic[(pf,ps)] = colls
#     print(pf, ps, 'average collisions to win:', sum(colls)/runs)
# with open('SColls' + str(frog_periods) + str(stork_periods) + str(random.randint(0,10000)) + ', runs= ' + str(runs), 'wb') as fp:
#     pickle.dump(all_colls_dic, fp)

playGame()
pygame.quit()
