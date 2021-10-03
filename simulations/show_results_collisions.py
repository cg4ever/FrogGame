import matplotlib.pyplot as plt
import pickle
import os
import numpy as np


sourceFileDir = os.path.dirname(os.path.abspath(__file__))
os.chdir(sourceFileDir)

simulation_dir = 'simulation_data'

path = os.path.join(simulation_dir, 'data_of_collisions_1000')

with open(path, 'rb') as fp:
    dic = pickle.load(fp)

for key,values in dic.items():
    print(key, 'number of wins = ', sum(1 for i in values if i < 3))
    runs = len(values)

# del dic[(50,50)], dic[(50,100)], dic[(50,125)], dic[(75,125)], dic[(100,50)], dic[(100,75)], dic[(125,50)], dic[(125,75)], dic[(125,100)], dic[(75,50)], dic[(50,75)]

fig, ax = plt.subplots()
ax.set_title('Boxplot of simulation results with ' + str(runs) + ' runs')
ax.boxplot(dic.values(), patch_artist=True)
ax.set_xticklabels(dic.keys())
ax.yaxis.grid(True)
ax.set_xlabel('Different periods $(p_F, p_S)$')
ax.set_ylabel('Number of collisions until win')
plt.show()