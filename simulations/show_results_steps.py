import matplotlib.pyplot as plt
import pickle
import os
import numpy as np


sourceFileDir = os.path.dirname(os.path.abspath(__file__))
os.chdir(sourceFileDir)

simulation_dir = 'simulation_data'

path = os.path.join(simulation_dir, 'data_of_steps_1000')

with open(path, 'rb') as fp:
    dic = pickle.load(fp)

for key,values in dic.items():
    print(key, 'mean = ', np.mean(values))
    print('std = ', np.std(values))
    runs = len(values)


fig, ax = plt.subplots()
ax.set_title('Boxplot of simulation results with ' + str(runs) + ' runs')
ax.boxplot(dic.values(), patch_artist=True)
ax.set_xticklabels(dic.keys())
ax.yaxis.grid(True)
ax.set_xlabel('Different periods (pf, ps)')
ax.set_ylabel('Number of collisions until win')
plt.show()