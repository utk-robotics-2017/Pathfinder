from Tkinter import *
from tkFileDialog import askopenfilename
from tkFileDialog import asksaveasfilename
from PIL import Image, ImageTk
import cv2
import csv
import json
import math
import sys
from Structs.TrajectoryConfig import TrajectoryConfig
from Structs.Waypoint import Waypoint
from TrajectoryGenerator import TrajectoryGenerator
from SwerveModifier import SwerveModifier
from TankModifier import TankModifier


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


class DisplayWaypoint:
    def __init__(self, x, y, theta, root, index, list_, redraw):
        self.x = DoubleVar()
        self.x.set(x)
        self.x.trace('w', self.updatePoint)

        self.y = DoubleVar()
        self.y.set(y)
        self.y.trace('w', self.updatePoint)

        self.theta = DoubleVar()
        self.theta.set(theta)
        self.theta.trace('w', self.updatePoint)

        self.xEntry = Entry(root, textvariable=self.x)
        self.xEntry.grid(row=17 + index, column=1)
        self.yEntry = Entry(root, textvariable=self.y)
        self.yEntry.grid(row=17 + index, column=2)
        self.thetaEntry = Entry(root, textvariable=self.theta)
        self.thetaEntry.grid(row=17 + index, column=3)

        self.deleteButton = Button(root, text="-", command=self.delete)
        self.deleteButton.grid(row=17 + index, column=4)

        self.list = list_
        self.index = index
        self.redraw = redraw

    def changeIndex(self, index):
        self.xEntry.grid(row=17 + index, column=1)
        self.yEntry.grid(row=17 + index, column=2)
        self.thetaEntry.grid(row=17 + index, column=3)
        self.deleteButton.grid(row=17 + index, column=4)
        self.index = index

    def updatePoint(self, *args):
        # if the textbox isn't a number don't update
        try:
            self.x.get()
            self.y.get()
            self.theta.get()
            self.redraw()
        except:
            pass

    def delete(self):
        self.xEntry.destroy()
        self.yEntry.destroy()
        self.thetaEntry.destroy()
        self.deleteButton.destroy()
        del self.list[self.index]
        for i in range(len(self.list)):
            self.list[i].changeIndex(i)
        self.redraw()


class Application(Frame):

    def __init__(self, master=None):
        self.root = master
        Frame.__init__(self, master)
        # width x height + x_offset + y_offset:
        #self.root.geometry("1000x700+0+0")
        self.createHeaderBar()
        self.createWidgets()

        self.opencv_image = None
        self.opencv_image_marked = None

        self.waypoints = []

        self.trajectory_segments = []
        self.tank_left_segments = []
        self.tank_right_segments = []
        self.swerve_front_left_segments = []
        self.swerve_front_right_segments = []
        self.swerve_back_left_segments = []
        self.swerve_back_right_segments = []

    def createHeaderBar(self):
        menubar = Menu(self.root)

        viewmenu = Menu(menubar, tearoff=0)

        self.viewWaypoints = BooleanVar()
        self.viewWaypoints.set(True)
        self.viewWaypoints.trace('w', self.updateDraw)
        viewmenu.add_checkbutton(label="View Waypoints", var=self.viewWaypoints)

        self.viewTrajectory = BooleanVar()
        self.viewTrajectory.set(True)
        self.viewTrajectory.trace('w', self.updateDraw)
        viewmenu.add_checkbutton(label="View Trajectory", var=self.viewTrajectory)

        self.viewTankTrajectory = BooleanVar()
        self.viewTankTrajectory.set(False)
        self.viewTankTrajectory.trace('w', self.updateDraw)
        viewmenu.add_checkbutton(label="View Tank Trajectory", var=self.viewTankTrajectory)

        self.viewSwerveTrajectory = BooleanVar()
        self.viewSwerveTrajectory.set(False)
        self.viewSwerveTrajectory.trace('w', self.updateDraw)
        viewmenu.add_checkbutton(label="View Swerve Trajectory", var=self.viewSwerveTrajectory)

        menubar.add_cascade(label="View", menu=viewmenu)

        importmenu = Menu(menubar, tearoff=0)
        importmenu.add_command(label="Open Course Image", command=self.openCourseImage)
        importmenu.add_command(label="Import Config", command=self.importConfig)
        importmenu.add_command(label="Import Waypoints", command=self.importWaypoints)
        menubar.add_cascade(label="Import", menu=importmenu)

        exportmenu = Menu(menubar, tearoff=0)
        exportmenu.add_command(label="Export Config", command=self.exportConfig)
        exportmenu.add_command(label="Export Waypoints", command=self.exportWaypoints)
        exportmenu.add_command(label="Export Trajectories", command=self.exportTrajectories)
        exportmenu.add_command(label="Export All", command=self.exportAll)
        menubar.add_cascade(label="Export", menu=exportmenu)

        self.root.config(menu=menubar)

    def openCourseImage(self):
        options = {'filetypes': [('JPEG', '.jpg'), ('PNG', '.png')], 'initialdir': '.', 'parent': self.root}

        imageFilename = askopenfilename(**options)
        if(imageFilename != ""):
            self.openImageButton.grid_forget()
            self.opencv_image = cv2.imread(imageFilename)
            cv2.putText(self.opencv_image, "X", (20, 15), cv2.FONT_HERSHEY_PLAIN, 1.0, (0, 0, 255))
            cv2.line(self.opencv_image, (20, 20), (30, 20),  (0, 0, 255), 2)
            cv2.putText(self.opencv_image, "Y", (5, 30), cv2.FONT_HERSHEY_PLAIN, 1.0, (255, 0, 0))
            cv2.line(self.opencv_image, (20, 20), (20, 30),  (255, 0, 0), 2)
            self.opencv_image_marked = self.opencv_image.copy()
            self.setImage()
            self.updateDraw()

    def setImage(self):
        image = Image.fromarray(cv2.cvtColor(self.opencv_image_marked, cv2.COLOR_BGR2RGB))
        photoimage = ImageTk.PhotoImage(image)
        self.image = Label(self.root, image=photoimage)
        self.image.image = photoimage
        self.image.grid(row=0, column=0, rowspan=50)
        if self.viewWaypoints.get():
            self.image.bind('<Button-1>', self.mouse_click)
        (self.imageWidth, self.imageLength) = image.size

    def mouse_click(self, event):

        courseWidth = self.courseWidth.get()
        courseLength = self.courseLength.get()

        if not is_number(courseWidth) and not is_number(courseLength):
            self.configError.set("Course Width is not set\nCourse Length is not set")
            return
        elif not is_number(courseWidth):
            self.configError.set("Course Width is not set")
            return
        elif not is_number(courseLength):
            self.configError.set("Course Length is not set")
            return
        else:
            self.configError.set("")

        courseWidth = float(courseWidth)
        courseLength = float(courseLength)

        if courseWidth <= 0.0 and courseLength <= 0.0:
            self.configError.set("Course Width needs to be a positive number\nCourse Length needs to be a positive number")
            return
        elif courseWidth <= 0.0:
            self.configError.set("Course Width needs to be a positive number")
            return
        elif courseLength <= 0.0:
            self.configError.set("Course Length needs to be a positive number")
            return
        else:
            self.configError.set("")

        # unit conversion
        x = float(event.x * courseWidth / self.imageWidth)
        y = float(event.y * courseLength / self.imageLength)

        self.waypoints.append(DisplayWaypoint(x, y, 0.0, self.root, len(self.waypoints), self.waypoints, self.updateDraw))
        self.updateDraw()

    def updateDraw(self, *args):
        courseWidth = self.courseWidth.get()
        courseLength = self.courseLength.get()

        if not is_number(courseWidth) and not is_number(courseLength):
            self.configError.set("Course Width is not set\nCourse Length is not set")
            return
        elif not is_number(courseWidth):
            self.configError.set("Course Width is not set")
            return
        elif not is_number(courseLength):
            self.configError.set("Course Length is not set")
            return
        else:
            self.configError.set("")

        courseWidth = float(courseWidth)
        courseLength = float(courseLength)

        if courseWidth <= 0.0 and courseLength <= 0.0:
            self.configError.set("Course Width needs to be a positive number\nCourse Length needs to be a positive number")
            return
        elif courseWidth <= 0.0:
            self.configError.set("Course Width needs to be a positive number")
            return
        elif courseLength <= 0.0:
            self.configError.set("Course Length needs to be a positive number")
            return
        else:
            self.configError.set("")

        if not self.opencv_image is None:
            self.opencv_image_marked = self.opencv_image.copy()

            if self.viewWaypoints.get():
                for displayWaypoint in self.waypoints:
                    try:
                        # unit conversion
                        x = int(displayWaypoint.x.get() * self.imageWidth / courseWidth)
                        y = int(displayWaypoint.y.get() * self.imageLength / courseLength)

                        cv2.circle(self.opencv_image_marked, (x, y), 3, (0, 255, 0), 2)
                        p1 = (x, y)
                        line_length = 15
                        theta = displayWaypoint.theta.get()
                        p2 = (int(x + line_length * math.cos(math.radians(float(theta)))), int(y + line_length * math.sin(math.radians(float(theta)))))
                        cv2.line(self.opencv_image_marked, p1, p2,  (0, 0, 255), 2)
                    except:
                        pass
                self.importWaypointsButton.grid(row=19 + len(self.waypoints), column=1, columnspan=3)
                if len(self.waypoints) > 0:
                    self.clearWaypointsButton.grid(row=18 + len(self.waypoints), column=1, columnspan=3)
                    self.exportWaypointsButton.grid(row=20 + len(self.waypoints), column=1, columnspan=3)
            self.updateTrajectory()
            if self.viewTrajectory.get():
                for i in range(len(self.trajectory_segments) - 1):
                    curr_seg = self.trajectory_segments[i]
                    next_seg = self.trajectory_segments[i + 1]

                    p1 = (int(self.imageWidth * curr_seg.x / float(courseWidth)), int(self.imageLength * curr_seg.y / float(courseLength)))
                    p2 = (int(self.imageWidth * next_seg.x / float(courseWidth)), int(self.imageLength * next_seg.y / float(courseLength)))

                    cv2.line(self.opencv_image_marked, p1, p2, (0, 0, 255), 2)
            if self.viewTankTrajectory.get():
                for i in range(len(self.tank_left_segments) - 1):
                    curr_seg = self.tank_left_segments[i]
                    next_seg = self.tank_left_segments[i + 1]

                    p1 = (int(self.imageWidth * curr_seg.x / float(courseWidth)), int(self.imageLength * curr_seg.y / float(courseLength)))
                    p2 = (int(self.imageWidth * next_seg.x / float(courseWidth)), int(self.imageLength * next_seg.y / float(courseLength)))

                    cv2.line(self.opencv_image_marked, p1, p2, (255, 0, 0), 2)

                    curr_seg = self.tank_right_segments[i]
                    next_seg = self.tank_right_segments[i + 1]

                    p1 = (int(self.imageWidth * curr_seg.x / float(courseWidth)), int(self.imageLength * curr_seg.y / float(courseLength)))
                    p2 = (int(self.imageWidth * next_seg.x / float(courseWidth)), int(self.imageLength * next_seg.y / float(courseLength)))

                    cv2.line(self.opencv_image_marked, p1, p2, (0, 255, 0), 2)
            if self.viewSwerveTrajectory.get():
                for i in range(len(self.swerve_front_left_segments) - 1):
                    curr_seg = self.swerve_front_left_segments[i]
                    next_seg = self.swerve_front_left_segments[i + 1]

                    p1 = (int(self.imageWidth * curr_seg.x / float(courseWidth)), int(self.imageLength * curr_seg.y / float(courseLength)))
                    p2 = (int(self.imageWidth * next_seg.x / float(courseWidth)), int(self.imageLength * next_seg.y / float(courseLength)))

                    cv2.line(self.opencv_image_marked, p1, p2, (255, 255, 0), 2)

                    curr_seg = self.swerve_front_right_segments[i]
                    next_seg = self.swerve_front_right_segments[i + 1]

                    p1 = (int(self.imageWidth * curr_seg.x / float(courseWidth)), int(self.imageLength * curr_seg.y / float(courseLength)))
                    p2 = (int(self.imageWidth * next_seg.x / float(courseWidth)), int(self.imageLength * next_seg.y / float(courseLength)))

                    cv2.line(self.opencv_image_marked, p1, p2, (127, 127, 255), 2)

                    curr_seg = self.swerve_back_left_segments[i]
                    next_seg = self.swerve_back_left_segments[i + 1]

                    p1 = (int(self.imageWidth * curr_seg.x / float(courseWidth)), int(self.imageLength * curr_seg.y / float(courseLength)))
                    p2 = (int(self.imageWidth * next_seg.x / float(courseWidth)), int(self.imageLength * next_seg.y / float(courseLength)))

                    cv2.line(self.opencv_image_marked, p1, p2, (255, 0, 255), 2)

                    curr_seg = self.swerve_back_right_segments[i]
                    next_seg = self.swerve_back_right_segments[i + 1]

                    p1 = (int(self.imageWidth * curr_seg.x / float(courseWidth)), int(self.imageLength * curr_seg.y / float(courseLength)))
                    p2 = (int(self.imageWidth * next_seg.x / float(courseWidth)), int(self.imageLength * next_seg.y / float(courseLength)))

                    cv2.line(self.opencv_image_marked, p1, p2, (0, 255, 255), 2)
            self.setImage()

    def importConfig(self):
        options = {'filetypes': [('JSON', '.json')], 'initialdir': '.', 'parent': self.root}
        filename = askopenfilename(**options)
        if(filename != ""):
            json_file = open(filename)
            file_text = ""
            for line in json_file:
                file_text = file_text + line
            self.config = json.loads(file_text)

            self.courseWidth.set(self.config['course_width'])
            self.courseLength.set(self.config['course_length'])
            self.maxVelocity.set(self.config['max_velocity'])
            self.maxAcceleration.set(self.config['max_acceleration'])
            self.maxJerk.set(self.config['max_jerk'])
            self.sampleCount.set(self.config['sample_count'])
            self.timeStep.set(self.config['time_step'])
            self.wheelbaseWidth.set(self.config['wheelbase_width'])
            self.wheelbaseLength.set(self.config['wheelbase_length'])

            self.updateDraw()

    def exportConfig(self):
        options = {'defaultextension': '.json', 'filetypes': [('JSON', '.json')], 'initialfile': 'pathfinder_config.json', 'initialdir': '.', 'parent': self.root}
        filename = asksaveasfilename(**options)
        if(filename != ""):
            try:
                config = dict({'course_width': self.courseWidth.get(),
                               'course_length': self.courseLength.get(),
                               'max_velocity': self.maxVelocity.get(),
                               'max_acceleration': self.maxAcceleration.get(),
                               'max_jerk': self.maxJerk.get(),
                               'sample_count': self.sampleCount.get(),
                               'time_step': self.timeStep.get(),
                               'wheelbase_width': self.wheelbaseWidth.get(),
                               'wheelbase_length': self.wheelbaseLength.get()})
            except:
                self.configError.set("One of the config items is not a number")
                return

            configFile = open(filename, 'w')
            configFile.write(json.dumps(config, sort_keys=True, indent=4, separators=(',', ': ')))

    def clearWaypoints(self):
        for i in range(len(self.waypoints)):
            self.waypoints[0].delete()
        self.updateDraw()
        self.clearWaypointsButton.grid_forget()
        self.exportWaypointsButton.grid_forget()

    def importWaypoints(self):
        options = {'defaultextension': '.csv',
                   'filetypes': [('CSV', '.csv')],
                   'initialfile': 'waypoints.csv',
                   'initialdir': '.',
                   'parent': self.root
                   }
        filename = askopenfilename(**options)
        if filename != "":
            self.waypoints = []
            with open(filename) as csvfile:
                reader = csv.DictReader(csvfile)
                i = 0
                for row in reader:
                    self.waypoints.append(DisplayWaypoint(float(row['x']), float(row['y']), float(row['theta']), self.root, i, self.waypoints, self.updateDraw))
                    i = i + 1
                self.updateDraw()

    def exportWaypoints(self):
        options = {'defaultextension': '.csv',
                   'filetypes': [('CSV', '.csv')],
                   'initialfile': 'waypoints.csv',
                   'initialdir': '.',
                   'parent': self.root
                   }

        filename = asksaveasfilename(**options)
        if filename != "":
            with open(filename, 'w') as csvfile:
                fieldnames = ['x', 'y', 'theta']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for waypoint in self.waypoints:
                    writer.writerow({'x': waypoint.x.get(), 'y': waypoint.y.get(), 'theta': waypoint.theta.get()})

    def updateTrajectory(self):
        self.trajectory_segments = []
        self.tank_left_segments = []
        self.tank_right_segments = []
        self.swerve_front_left_segments = []
        self.swerve_front_right_segments = []
        self.swerve_back_left_segments = []
        self.swerve_back_right_segments = []
        if len(self.waypoints) == 0:
            return
        try:
            trajectoryConfig = TrajectoryConfig()
            trajectoryConfig.max_v = self.maxVelocity.get()
            trajectoryConfig.max_a = self.maxAcceleration.get()
            trajectoryConfig.max_j = self.maxJerk.get()
            trajectoryConfig.dt = self.timeStep.get()
            trajectoryConfig.sample_count = self.sampleCount.get()

            trajectoryWaypoints = []
            for displayWaypoint in self.waypoints:
                trajectoryWaypoints.append(Waypoint(displayWaypoint.x.get(), displayWaypoint.y.get(), displayWaypoint.theta.get()))

            generator = TrajectoryGenerator(trajectoryWaypoints, trajectoryConfig)
            self.trajectory_segments = generator.generate()

            tankModifier = TankModifier(self.trajectory_segments, self.wheelbaseWidth.get())
            self.tank_left_segments = tankModifier.get_left_trajectory()
            self.tank_right_segments = tankModifier.get_right_trajectory()

            swerveModifier = SwerveModifier(self.trajectory_segments, self.wheelbaseWidth.get(), self.wheelbaseLength.get())
            self.swerve_front_left_segments = swerveModifier.get_front_left_trajectory()
            self.swerve_front_right_segments = swerveModifier.get_front_right_trajectory()
            self.swerve_back_left_segments = swerveModifier.get_back_left_trajectory()
            self.swerve_back_right_segments = swerveModifier.get_back_right_trajectory()

        except:
            print "Unexpected error:", sys.exc_info()[0]
            return

    def write_trajectory(self, file_, segments):
        fieldnames = ['dt', 'x', 'y', 'position', 'velocity', 'acceleration', 'jerk', 'heading']
        writer = csv.DictWriter(file_, fieldnames=fieldnames)
        writer.writeheader()
        for segment in segments:
            writer.writerow({'dt': segment.dt, 'x': segment.x, 'y': segment.y, 'position': segment.position, 'velocity': segment.velocity, 'acceleration': segment.acceleration, 'jerk': segment.jerk, 'heading': segment.heading})

    def exportTrajectories(self):
        options = {'defaultextension': '.csv',
                   'filetypes': [('CSV', '.csv')],
                   'initialfile': 'trajectory.csv',
                   'initialdir': '.',
                   'parent': self.root
                   }
        filename = asksaveasfilename(**options)
        if filename != "":
            self.write_trajectory(open(filename, 'w'), self.trajectory_segments)

            split_filename = filename.rsplit('/')

            path = ""
            for i in range(len(split_filename) - 1):
                path = path + split_filename[i] + "/"

            filename = split_filename[-1]

            #tank
            self.write_trajectory(open(path + "left_" + filename, 'w'), self.tank_left_segments)
            self.write_trajectory(open(path + "right_" + filename, 'w'), self.tank_right_segments)

            #swerve
            self.write_trajectory(open(path + "front_left_" + filename, 'w'), self.swerve_front_left_segments)
            self.write_trajectory(open(path + "front_right_" + filename, 'w'), self.swerve_front_right_segments)
            self.write_trajectory(open(path + "back_left_" + filename, 'w'), self.swerve_back_left_segments)
            self.write_trajectory(open(path + "back_right_" + filename, 'w'), self.swerve_back_right_segments)

    def exportAll(self):
        return

    def createWidgets(self):

        self.openImageButton = Button(self.root, text="Open Course Image", command=self.openCourseImage)
        self.openImageButton.grid(row=0, column=0, rowspan=25, padx=30, pady=30)

        Label(self.root, text="Configuration", font=("Helvetica", 20)).grid(row=0, column=1, columnspan=2)

        Label(self.root, text="Course Width (in)").grid(row=1, column=1)
        self.courseWidth = DoubleVar()
        self.courseWidth.set(0.0)
        Entry(self.root, textvariable=self.courseWidth).grid(row=1, column=2)

        Label(self.root, text="Course Length (in)").grid(row=2, column=1)
        self.courseLength = DoubleVar()
        self.courseLength.set(0.0)
        Entry(self.root, textvariable=self.courseLength).grid(row=2, column=2)

        Label(self.root, text="Max Velocity (in/s)").grid(row=3, column=1)
        self.maxVelocity = DoubleVar(0.0)
        self.maxVelocity.set(0.0)
        Entry(self.root, textvariable=self.maxVelocity).grid(row=3, column=2)

        Label(self.root, text="Max Acceleration (in/s^2)").grid(row=4, column=1)
        self.maxAcceleration = DoubleVar(0.0)
        self.maxAcceleration.set(0.0)
        Entry(self.root, textvariable=self.maxAcceleration).grid(row=4, column=2)

        Label(self.root, text="Max Jerk (in/s^3)").grid(row=5, column=1)
        self.maxJerk = DoubleVar()
        self.maxJerk.set(0.0)
        Entry(self.root, textvariable=self.maxJerk).grid(row=5, column=2)

        Label(self.root, text="Sample Count").grid(row=6, column=1)
        self.sampleCount = IntVar()
        self.sampleCount.set(0)
        Entry(self.root, textvariable=self.sampleCount).grid(row=6, column=2)

        Label(self.root, text="Time Step (s)").grid(row=7, column=1)
        self.timeStep = DoubleVar()
        self.timeStep.set(0.0)
        Entry(self.root, textvariable=self.timeStep).grid(row=7, column=2)

        Label(self.root, text="Wheelbase Width (in)").grid(row=8, column=1)
        self.wheelbaseWidth = DoubleVar()
        self.wheelbaseWidth.set(0.0)
        Entry(self.root, textvariable=self.wheelbaseWidth).grid(row=8, column=2)

        Label(self.root, text="Wheelbase Length (in)").grid(row=9, column=1)
        self.wheelbaseLength = DoubleVar()
        self.wheelbaseLength.set(0.0)
        Entry(self.root, textvariable=self.wheelbaseLength).grid(row=9, column=2)

        self.configError = StringVar()
        self.configError.set("")
        Label(self.root, textvariable=self.configError, fg="red").grid(row=10, column=1, columnspan=2)

        Button(self.root, text="Import Config", command=self.importConfig).grid(row=11, column=1, columnspan=2)
        Button(self.root, text="Export Config", command=self.exportConfig).grid(row=12, column=1, columnspan=2)

        Label(self.root, text="Waypoints", font=("Helvetica", 20)).grid(row=15, column=1, columnspan=2)

        Label(self.root, text="X (in)").grid(row=16, column=1)
        Label(self.root, text="Y (in)").grid(row=16, column=2)
        Label(self.root, text="Heading (degrees)").grid(row=16, column=3)

        self.clearWaypointsButton = Button(self.root, text="Clear Waypoints", command=self.clearWaypoints)
        self.importWaypointsButton = Button(self.root, text="Import Waypoints", command=self.importWaypoints)
        self.importWaypointsButton.grid(row=17, column=1, columnspan=3)
        self.exportWaypointsButton = Button(self.root, text="Export Waypoints", command=self.exportWaypoints)

        Label(self.root, text="Trajectory", font=("Helvetica", 20)).grid(row=0, column=3, columnspan=2)
        Button(self.root, text="Export Trajectory", command=self.exportTrajectories).grid(row=1, column=3, columnspan=2)

root = Tk()
root.title("Pathfinder")
app = Application(master=root)
app.mainloop()
root.destroy()
