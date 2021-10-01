import matplotlib.pyplot as plt
import pickle
import os
import numpy as np


sourceFileDir = os.path.dirname(os.path.abspath(__file__))
os.chdir(sourceFileDir)

simulation_dir = 'simulation_data'

path1 = os.path.join(simulation_dir, 'Strategy50;75;1-20_3292')
path2 = os.path.join(simulation_dir, 'Strategy75;100;1-20_8069')

with open (path1, 'rb') as fp:
    dic1 = pickle.load(fp)

with open (path2, 'rb') as fp:
    dic2 = pickle.load(fp)

acting_times_dic = dic1['at']
winning_times_dic = dic1['wt']
wins_dic = dic1['w']

acting_times_dic2 = dic2['at']
winning_times_dic2 = dic2['wt']
wins_dic2 = dic2['w']


fig, ax = plt.subplots()
ax.set_title(str(dic2['runs']) + ' runs with two different pairs of periods' )
ax.plot(wins_dic.keys(), wins_dic.values(), label= '(50, 75)')
ax.plot(wins_dic2.keys(), wins_dic2.values(), label= '(75, 100)')
# ax.plot(wins_dic.keys(), y, label= 'Vergleichsgerade')
ax.set_xlabel('Different strategies')
ax.set_ylabel('Number of wins')
plt.xticks([i for i in range(1,20)])
ax.legend()

plt.show()