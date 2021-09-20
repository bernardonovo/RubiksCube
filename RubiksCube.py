import sys


from panda3d.core import *
from direct.showbase.ShowBase import ShowBase
from direct.interval.IntervalGlobal import LerpHprInterval, Func, Sequence
from direct.task import Task
from direct.gui.OnscreenText import OnscreenText

RGB_BLACK = (0, 0, 0, 1)

# Defines the attributes of each face of a rubik's cube
# - "color" is the RBG value of face's colour
# - "normal" is the position of the face (using coordinates x, y, z) from the centre of the scene
# - "face_vertices" defines the (x, y, z) coordinates of each of the face's vertices
#
# Coordinate (0, 0, 0) is the centre of the scene (which also happens to be the centre of the rubik's cube)
# Coordinates range from -1 to 1. Each represents a distance of 100% from point zero (centre of the scene/cube)
cube_data = {
    'down': {
        'color': (255, 255, 255, 1),  # White
        'normal': (0, 0, -1),
        'face_vertices': (
            (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1)
        )
    },
    'up': {
        'color': (255, 215, 0, 1),  # Yellow
        'normal': (0, 0, 1),
        'face_vertices': (
            (-1, -1, 1), (-1, 1, 1), (1, 1, 1), (1, -1, 1)
        )
    },
    'left': {
        'color': (0, 120, 50, 1),  # Green
        'normal': (-1, 0, 0),
        'face_vertices': (
            (-1, -1, -1), (-1, 1, -1), (-1, 1, 1), (-1, -1, 1)
        )
    },
    'right': {
        'color': (0, 70, 160, 1),  # Blue
        'normal': (1, 0, 0),
        'face_vertices': (
            (1, -1, -1), (1, -1, 1), (1, 1, 1), (1, 1, -1)
        )
    },
    'back': {
        'color': (200, 0, 0, 1),  # Red
        'normal': (0, 1, 0),
        'face_vertices': (
            (-1, 1, -1), (1, 1, -1), (1, 1, 1), (-1, 1, 1)
        )
    },
    'front': {
        'color': (255, 128, 0, 1),  # Orange
        'normal': (0, -1, 0),
        'face_vertices': (
            (-1, -1, -1), (-1, -1, 1), (1, -1, 1), (1, -1, -1)
        )
    }
}

# Defines each "row" of a rubik's cube, and the attributes these rows possess
# - "axis" defines the axis that will be rotated, from a 3D perspective. The values (90./-90.) represent the degree of
#   rotation of each movement (in this case '90.' = 1/4 of a 360 degree rotation)
# - "positive" and "negative" are used in update_cube_state() and define the direction of rotation
row_data = {
    "front": {
        "axis": VBase3(0., 0., 90.),
        "rotation": {
            "positive": [[0, 0, -1], [0, 1, 0], [1, 0, 0]],
            "negative": [[0, 0, 1], [0, 1, 0], [-1, 0, 0]]
        }
    },
    "back": {
        "axis": VBase3(0., 0., -90.),
        "rotation": {
            "positive": [[0, 0, 1], [0, 1, 0], [-1, 0, 0]],
            "negative": [[0, 0, -1], [0, 1, 0], [1, 0, 0]]
        }
    },
    "left": {
        "axis": VBase3(0., 90., 0.),
        "rotation": {
            "positive": [[1, 0, 0], [0, 0, 1], [0, -1, 0]],
            "negative": [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
        }
    },
    "right": {
        "axis": VBase3(0., -90., 0.),
        "rotation": {
            "positive": [[1, 0, 0], [0, 0, -1], [0, 1, 0]],
            "negative": [[1, 0, 0], [0, 0, 1], [0, -1, 0]]
        }
    },
    "down": {
        "axis": VBase3(90., 0., 0.),
        "rotation": {
            "positive": [[0, 1, 0], [-1, 0, 0], [0, 0, 1]],
            "negative": [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
        }
    },
    "up": {
        "axis": VBase3(-90., 0., 0.),
        "rotation": {
            "positive": [[0, -1, 0], [1, 0, 0], [0, 0, 1]],
            "negative": [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]
        }
    },
    "equator": {
        "axis": VBase3(-90., 0., 0.),
        "rotation": {
            "positive": [[0, -1, 0], [1, 0, 0], [0, 0, 1]],
            "negative": [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]
        }
    },
    "centre_front": {
        "axis": VBase3(0., -90., 0.),
        "rotation": {
            "positive": [[1, 0, 0], [0, 0, -1], [0, 1, 0]],
            "negative": [[1, 0, 0], [0, 0, 1], [0, -1, 0]]
        }
    },
    "centre_right": {
        "axis": VBase3(0., 0., 90.),
        "rotation": {
            "positive": [[0, 0, -1], [0, 1, 0], [1, 0, 0]],
            "negative": [[0, 0, 1], [0, 1, 0], [-1, 0, 0]]
        }
    }
}


# Figures out if the cube piece coordinates contain a face defined in "normal", meaning it is visible
def is_visible_face(normal, coordinates):
    for i in range(3):
        if normal[i] != 0:
            if normal[i] == coordinates[i]:
                return True
    return False


# Add a single cube piece to the rubik's cube
def add_cube_piece(parent, x, y, z, position, cube_state, rows):
    vformat = GeomVertexFormat.getV3n3cp()
    vdata = GeomVertexData('rubiks_cube', vformat, Geom.UHStatic)
    tris = GeomTriangles(Geom.UHStatic)

    vertexWriter = GeomVertexWriter(vdata, "vertex")
    colorWriter = GeomVertexWriter(vdata, "color")
    normalWriter = GeomVertexWriter(vdata, "normal")

    vcount = 0

    for face in cube_data:
        # Defines the orientation of the face
        normal = cube_data[face]['normal']
        # Defines the vertices of the face
        face_vertex_list = cube_data[face]['face_vertices']
        # Finds out the colour the face should use
        # We only want to paint external faces, while internal ones should be black
        if is_visible_face(normal, (x, y, z)):
            color = cube_data[face]['color']
        else:
            color = RGB_BLACK

        # Defines the properties for each cube piece (i.e., each polygon)
        # Properties include its 3d positioning in regards to the centre of the scene, and its external vertices
        # Each external face will have a colour, while internal faces will be painted black
        for face_vertex in face_vertex_list:
            vertexWriter.addData3f(face_vertex)
            if is_visible_face(normal, (x, y, z)):
                colorWriter.addData4i(color)
            else:
                colorWriter.addData4i(RGB_BLACK)
            normalWriter.addData3f(normal)

        # Adds vertices to each side of the cube piece being rendered
        vcount += 4
        tris.addVertices(vcount - 2, vcount - 3, vcount - 4)
        tris.addVertices(vcount - 4, vcount - 1, vcount - 2)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode("cubo_node")
    node.addGeom(geom)
    cube = parent.attachNewNode(node)
    cube.setScale(.48)
    cube.setPos(x, y, z)
    state = set()
    position[cube] = [x, y, z]
    cube_state[cube] = state

    if x == 1:
        rows["right"].append(cube)
        state.add("right")
    elif x == -1:
        rows["left"].append(cube)
        state.add("left")
    elif x == 0:
        rows["centre_front"].append(cube)
        state.add("centre_front")

    if y == 1:
        rows["back"].append(cube)
        state.add("back")
    elif y == -1:
        rows["front"].append(cube)
        state.add("front")
    elif y == 0:
        rows["centre_right"].append(cube)
        state.add("centre_right")

    if z == -1:
        rows["down"].append(cube)
        state.add("down")
    elif z == 1:
        rows["up"].append(cube)
        state.add("up")
    elif z == 0:
        rows["equator"].append(cube)
        state.add("equator")

    return cube


class RubiksCube(ShowBase):
    rows = {}
    pivots = {}
    rotations = {}
    position = {}
    cube_state = {}
    sec = Sequence()

    def __init__(self):
        ShowBase.__init__(self)

        self.graphicsEngine.renderFrame()

        # Prints on-screen instructions
        OnscreenText(text="Keys:", style=1, fg=(1, 1, 1, 1), pos=(-1.1, .90), scale=.07)
        OnscreenText(text="Up: U, shift-U", style=1, fg=(1, 1, 1, 1), pos=(-1.1, .80), scale=.05)
        OnscreenText(text="Down: D, shift-D", style=1, fg=(1, 1, 1, 1), pos=(-1.1, .70), scale=.05)
        OnscreenText(text="Left: L, shift-L", style=1, fg=(1, 1, 1, 1), pos=(-1.1, .60), scale=.05)
        OnscreenText(text="Right: R, shift-R", style=1, fg=(1, 1, 1, 1), pos=(-1.1, .50), scale=.05)
        OnscreenText(text="Front: F, shift-F", style=1, fg=(1, 1, 1, 1), pos=(-1.1, .40), scale=.05)
        OnscreenText(text="Back: B, shift-B", style=1, fg=(1, 1, 1, 1), pos=(-1.1, .30), scale=.05)
        OnscreenText(text="Equator: E, shift-E", style=1, fg=(1, 1, 1, 1), pos=(-1.1, .20), scale=.05)
        OnscreenText(text="Centre-right: S, shift-S", style=1, fg=(1, 1, 1, 1), pos=(-1.06, .10), scale=.05)
        OnscreenText(text="Centre-front: C, shift-C", style=1, fg=(1, 1, 1, 1), pos=(-1.06, .0), scale=.05)
        OnscreenText(text="Front view: K", style=1, fg=(1, 1, 1, 1), pos=(-1.1, -.10), scale=.05)
        OnscreenText(text="Back view: Z", style=1, fg=(1, 1, 1, 1), pos=(-1.1, -.20), scale=.05)
        OnscreenText(text="Press ENTER to start sequence", style=1, fg=(1, 1, 1, 1), pos=(0.9, -.70), scale=.05)
        OnscreenText(text="Press BACKSPACE to reset sequence", style=1, fg=(1, 1, 1, 1), pos=(0.9, -.80), scale=.05)
        OnscreenText(text="Press ESC to exit", style=1, fg=(1, 1, 1, 1), pos=(0.9, -.90), scale=.05)

        for row_id in row_data:
            self.rows[row_id] = []
            self.pivots[row_id] = self.render.attachNewNode('pivot_%s' % row_id)
            self.rotations[row_id] = {"hpr": row_data[row_id]['axis']}

        # Renders each piece of the rubik's cube
        for x in (-1, 0, 1):
            for y in (-1, 0, 1):
                for z in (-1, 0, 1):
                    add_cube_piece(self.render, x, y, z, self.position, self.cube_state, self.rows)

        # Positions camera to point at the rubik's cube
        self.cam.setPos(7, -10, 6)
        self.cam.lookAt(0., 0., 0.)

        # Registers all keys that are valid as cube movements
        self.accept_input()

        # Registers all other keys that can always be accepted
        self.accept("escape", sys.exit)
        self.accept("k", self.show_front)
        self.accept("z", self.show_back)

        # Starts the camera task
        self.taskMgr.add(self.spinCameraTask, "SpinCameraTask")

    def reparent_cubes(self, row_id):
        pivot = self.pivots[row_id]
        children = pivot.getChildren()
        children.wrtReparentTo(self.render)
        pivot.clearTransform()
        children.wrtReparentTo(pivot)
        for cube in self.rows[row_id]:
            cube.wrtReparentTo(pivot)

    def update_cube_state(self, row_id, neg_rotation=False):
        for cube in self.rows[row_id]:
            old_state = self.cube_state[cube]
            new_state = set()
            self.cube_state[cube] = new_state

            if neg_rotation:
                direction = "negative"
            else:
                direction = "positive"

            ##############
            # Coordinate X
            ##############
            new_pos = 0

            for j in range(3):
                new_pos = new_pos + int(self.position[cube][j]) * int(row_data[row_id]['rotation'][direction][j][0])

            if new_pos == 1:
                new_state.add("right")
            elif new_pos == -1:
                new_state.add("left")
            elif new_pos == 0:
                new_state.add("centre_front")
            pos_x = new_pos

            ##############
            # Coordinate Y
            ##############
            new_pos = 0
            for j in range(3):
                new_pos = new_pos + int(self.position[cube][j]) * int(row_data[row_id]['rotation'][direction][j][1])

            if new_pos == 1:
                new_state.add("back")
            elif new_pos == -1:
                new_state.add("front")
            elif new_pos == 0:
                new_state.add("centre_right")
            pos_y = new_pos

            ##############
            # Coordinate Z
            ##############
            new_pos = 0
            for j in range(3):
                new_pos = new_pos + int(self.position[cube][j]) * int(row_data[row_id]['rotation'][direction][j][2])

            if new_pos == 1:
                new_state.add("up")
            elif new_pos == -1:
                new_state.add("down")
            elif new_pos == 0:
                new_state.add("equator")
            pos_z = new_pos

            self.position[cube] = [pos_x, pos_y, pos_z]

            for prev_row_id in old_state - new_state:
                self.rows[prev_row_id].remove(cube)
            for prev_row_id in new_state - old_state:
                self.rows[prev_row_id].append(cube)

        self.sec = Sequence()

    # Adds a single movement to the sequence. The movement itself is registered in "accept_input()"
    def add_move(self, row_id, reverse=False):
        # TODO: reparent_cubes()
        self.sec.append(Func(self.reparent_cubes, row_id))

        # Defines the direction of a rotation in "row_id" and its speed (0.5s)
        rot = self.rotations[row_id]["hpr"]
        if reverse:
            rot = rot * -1.
        self.sec.append(LerpHprInterval(self.pivots[row_id], 0.5, rot))

        # Update the final/desired cube state in "row_id"
        # TODO: Am I right about this?
        self.sec.append(Func(self.update_cube_state, row_id, reverse))

    # This function has three purposes:
    # 1 - Registers all valid key inputs in a sequence
    # 2 - Calls a lambda function whenever a valid key is pressed
    # 3 - Starts the sequence when the user presses "enter"
    def accept_input(self):
        # <F> adds a positive Front rotation
        self.accept("f", lambda: self.add_move("front"))
        # <Shift+F> adds a negative Front rotation
        self.accept("shift-f", lambda: self.add_move("front", True))
        # <B> adds a positive Back rotation
        self.accept("b", lambda: self.add_move("back"))
        # <Shift+B> adds a negative Back rotation
        self.accept("shift-b", lambda: self.add_move("back", True))
        # <L> adds a positive Left rotation
        self.accept("l", lambda: self.add_move("left"))
        # <Shift+L> adds a negative Left rotation
        self.accept("shift-l", lambda: self.add_move("left", True))
        # <R> adds a positive Right rotation
        self.accept("r", lambda: self.add_move("right"))
        # <Shift+R> adds a negative Right rotation
        self.accept("shift-r", lambda: self.add_move("right", True))
        # <D> adds a positive Down rotation
        self.accept("d", lambda: self.add_move("down"))
        # <Shift+D> adds a negative Down rotation
        self.accept("shift-d", lambda: self.add_move("down", True))
        # <U> adds a positive Up rotation
        self.accept("u", lambda: self.add_move("up"))
        # <Shift+U> adds a negative Up rotation
        self.accept("shift-u", lambda: self.add_move("up", True))
        # <C> adds a positive Centre-front rotation
        self.accept("c", lambda: self.add_move("centre_front"))
        # <Shift+C> adds a negative Centre-front rotation
        self.accept("shift-c", lambda: self.add_move("centre_front", True))
        # <E> adds a positive Equator rotation
        self.accept("e", lambda: self.add_move("equator"))
        # <Shift+E> adds a negative Equator rotation
        self.accept("shift-e", lambda: self.add_move("equator", True))
        # <S> adds a positive Centre-right rotation
        self.accept("s", lambda: self.add_move("centre_right"))
        # <Shift+S> adds a negative Centre-right rotation
        self.accept("shift-s", lambda: self.add_move("centre_right", True))
        # <Enter> Starts the sequence
        self.accept("enter", self.start_sequence)
        # <backspace> Resets the sequence
        self.accept("backspace", self.reset_sequence)

    # Ignores all inputs while the sequence runs
    def ignore_input(self):
        self.ignore("f")
        self.ignore("shift-f")
        self.ignore("b")
        self.ignore("shift-b")
        self.ignore("l")
        self.ignore("shift-l")
        self.ignore("r")
        self.ignore("shift-r")
        self.ignore("d")
        self.ignore("shift-d")
        self.ignore("u")
        self.ignore("shift-u")
        self.ignore("enter")
        self.ignore("backspace")

    # Executes all movements in the sequence in the order they have been registered.
    # We also want to ignore most inputs while the sequence is being executed, while
    # still allowing the user to exit the application during all times.
    def start_sequence(self):
        # Do not allow input while the sequence is playing...
        self.ignore_input()
        # ...but accept input again once the sequence is finished. It also appends
        # accept_input() to the end of the sequence, meaning that it is executed
        # after all the other commands in the sequence have also been executed.
        self.sec.append(Func(self.accept_input))
        self.sec.start()
        # Create a new sequence, so no new moves will be appended to the started one.
        self.sec = Sequence()

    def reset_sequence(self):
        self.sec = Sequence()

    # Shows the front, right and top faces of the rubik's cube. This is the default view.
    def show_front(self):
        self.trackball.node().setHpr(0, 0, 0)

    # Shows the back, left and bottom faces of the rubik's cube.
    def show_back(self):
        self.trackball.node().setHpr(90, 180, 0)

    # This function starts the Panda3D camera task, which allows one to move the camera
    # using the mouse. I.e. by holding the middle button.
    def spinCameraTask(self, task):
        self.camera.setPos(0, 0, 0)
        return Task.cont


# Starts the Panda3D application
app = RubiksCube()
app.run()
