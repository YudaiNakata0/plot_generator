# plot_generator
Scripts for visualizing data from rosbag files (```.bag``` files) and ```.npz``` files.

GUI アプリ（`app/`）の使い方は [USAGE.md](USAGE.md) を参照。

## plot_Pose.py
+ Script for creating plots from Pose-type topics in rosbag files.
+ The xyz plot will be displayed first, followed by the roll-pitch-yaw plot.
+ The data converted to an ```.npz``` file will be saved in the ```data/``` directory.
  + contents of the generated ```.npz``` file
    + time, x, y, z, tx (=target x), ty, tz, roll, pitch, yaw, troll (=target roll), tpitch, tyaw
    + Default values of tx, ty, tz, troll, tpitch, tyaw are 0.
+ Minimum configuration for execution (run in the top directory):
  ```
  ./scripts/plot_Pose.py {rosbag file name} {topic name}
  ```
### Options
+ -x, -y, -z:
  + target value of x, y, z [m] (draw a line)
+ --rx, --ry, --rz:
  + range of the target value from the center of the target value [m] (draw a band)
+ --roll, --pitch, --yaw:
  + target value of roll, pitch, yaw [rad] (draw a line)
+ -s, -e:
  + start and end time of the plot [s]
+ --ox, --oy, --oz:
  + arguments to suppress the display of xyz plot respectively [None or not None]
  + ex: ```--ox 1``` means creating only y and z plots

## plot_from_npz.py
+ Script for creating plots from ```.npz``` files.
+ The input data file needs properties of time, x, y, z, tx, ty, tz.
+ Minimum configuration for execution (run in the top directory):
  ```
  ./scripts/plot_from_npz.py {npz file name}
  ```
### Options
+ --rx, --ry, --rz:
  + range of the target value from the center of the target value [m]
## image_extractor.py
+ Script for generating and saving images from Image-type topics in rosbag files.
+ Minimum configuration for execution (run in the top directory):
  ```
  ./scripts/image_extractor.py {rosbag file name} {topic name}
  ```
### Options
+ -o:
  + path to output directory
  + default: ```bag_extracted_images/```
+ -s, -e:
  + start and end time of image generation [s]
  + default: start 0, end 1000
+ -d:
  + duration of image generation [s]
  + default: 1
## draw_trajectory.py
+ Script for generating trajectory plot of xyz data from ```.npz``` files
+ The input data file needs properties of time, x, y, z, tx, ty, tz.
+ Draw 2D or 3D trajectory.
+ Draw a target area circle.
+ Minimum configuration for execution (run in the top directory):
  ```
  ./scripts/draw_trajectory.py {npz file name}
  ```
### Options
+ -m:
  + mode 2D->2, 3D->3
  + default: 2
+ -r:
  + radius of the target area [m]
+ --axis:
  + normal axis for 2D mode [x or y or z]
  + default: x
+ -a:
  + angled target circle flag [None or not None]
+ -p:
  + pitch angle of angled target circle [rad]
  + default: 0
+ -l:
  + legend display flag [None or not None]
  + default: 1
+ --yz_range:
  + display range of generated plot [m]
  + default: 0.01
