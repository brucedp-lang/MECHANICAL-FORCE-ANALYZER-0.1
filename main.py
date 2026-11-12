from drafter import *
from dataclasses import dataclass
import math
import copy

# DATA CLASSES

@dataclass
class Point:
    name: str
    x: int
    y: int
    fixed: bool
    connections: list

@dataclass
class Force:
    number: int
    point: str
    magnitude: float
    angle: float
    fixed_angle: bool

@dataclass
class Connection:
    point1: str
    point2: str

@dataclass
class Mechanism:
    name: str
    points: list
    forces: list
    connections: list

@dataclass
class State:
    mechanisms: list
    draft: Mechanism
    editing_index: int
    selected_index: int
    calculations_log: list
    results: list
    project_name: str

# HELPER FUNCTIONS

def find_point(mechanism, name):
    for point in mechanism.points:
        if point.name.upper() == name.upper():
            return point
    return None

def next_point_name(mechanism):
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if find_point(mechanism, letter) is None:
            return letter
    return None

def next_force_number(mechanism):
    if len(mechanism.forces) == 0:
        return 1

    return max(force.number for force in mechanism.forces) + 1

def valid_number(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def alphabetical_connections(mechanism, point):
    names = []

    for connection in mechanism.connections:
        if connection.point1 == point.name:
            names.append(connection.point2)

        elif connection.point2 == point.name:
            names.append(connection.point1)

    return sorted(names)


def update_connections(mechanism):
    for point in mechanism.points:
        point.connections = alphabetical_connections(
            mechanism, point
        )


def create_empty_mechanism(name="Untitled"):
    return Mechanism(name, [], [], [])


# GRAPH GENERATOR

def create_graph(mechanism):

    # Seven rows and seven columns represent -3 through 3.

    grid = []

    for row in range(7):
        grid.append(["." for column in range(7)])

    def grid_location(x, y):
        return 3 - y, x + 3

    # Draw connections first.

    for connection in mechanism.connections:

        p1 = find_point(mechanism, connection.point1)
        p2 = find_point(mechanism, connection.point2)

        if p1 is None or p2 is None:
            continue

        x1 = p1.x
        y1 = p1.y
        x2 = p2.x
        y2 = p2.y

        dx = x2 - x1
        dy = y2 - y1

        steps = max(abs(dx), abs(dy))

        if steps == 0:
            continue

        if dx == 0:
            symbol = "|"
        elif dy == 0:
            symbol = "-"
        elif dx * dy > 0:
            symbol = "/"
        else:
            symbol = "\\"

        for step in range(1, steps):

            x = round(x1 + dx * step / steps)
            y = round(y1 + dy * step / steps)

            row, column = grid_location(x, y)

            if grid[row][column] == ".":
                grid[row][column] = symbol

    # Draw force arrows.

    arrows = {
        (1, 0): ">",
        (-1, 0): "<",
        (0, 1): "^",
        (0, -1): "v",
        (1, 1): "^",
        (-1, 1): "^",
        (1, -1): "v",
        (-1, -1): "v"
    }

    for force in mechanism.forces:

        point = find_point(mechanism, force.point)

        if point is None:
            continue

        radians = math.radians(force.angle)

        fx = math.cos(radians)
        fy = math.sin(radians)

        direction = (
            round(fx),
            round(fy)
        )

        arrow = arrows.get(direction, ">")

        arrow_x = point.x + direction[0]
        arrow_y = point.y + direction[1]

        if -3 <= arrow_x <= 3 and -3 <= arrow_y <= 3:

            row, column = grid_location(
                arrow_x, arrow_y
            )

            if grid[row][column] == ".":
                grid[row][column] = arrow

    # Draw points last so they remain visible.

    for point in mechanism.points:

        if -3 <= point.x <= 3 and -3 <= point.y <= 3:

            row, column = grid_location(
                point.x, point.y
            )

            grid[row][column] = point.name

    # Convert graph to readable text.

    lines = []

    lines.append("             GRAPH")
    lines.append("")

    for row_index, row in enumerate(grid):

        y_value = 3 - row_index

        line = str(y_value).rjust(3) + "  "

        for symbol in row:
            line += str(symbol).center(4)

        lines.append(line)

    lines.append("     " + "".join(
        str(x).center(4) for x in range(-3, 4)
    ))

    lines.append("")
    lines.append("Points are letters.")
    lines.append("Connections: - | / \\")
    lines.append("Forces: ^ v < >")

    return "\n".join(lines)

# TABLE GENERATORS

def create_point_table(mechanism):

    lines = []

    lines.append("POINT TABLE")
    lines.append("Letter | X | Y | Fixed | Connections")
    lines.append("-----------------------------------")

    for point in sorted(
        mechanism.points,
        key=lambda p: p.name
    ):

        connections = ", ".join(
            alphabetical_connections(mechanism, point)
        )

        if connections == "":
            connections = "None"

        lines.append(
            point.name + " | " +
            str(point.x) + " | " +
            str(point.y) + " | " +
            str(point.fixed) + " | " +
            connections
        )

    if len(mechanism.points) == 0:
        lines.append("No points added.")

    return "\n".join(lines)


def create_force_table(mechanism):

    lines = []

    lines.append("FORCE TABLE")
    lines.append("Number | Force | Angle | Fixed Angle")
    lines.append("-------------------------------------")

    for force in sorted(
        mechanism.forces,
        key=lambda f: f.number
    ):

        lines.append(
            str(force.number) + " | " +
            str(round(force.magnitude, 3)) + " N | " +
            str(round(force.angle, 3)) + " degrees | " +
            str(force.fixed_angle)
        )

    if len(mechanism.forces) == 0:
        lines.append("No forces added.")

    return "\n".join(lines)

# STATIC EQUILIBRIUM SOLVER

def solve_linear_system(matrix, values):

    # Gaussian elimination.
    # Free variables are assigned zero when possible.

    if len(matrix) == 0:
        return [], 0, True

    A = [row[:] for row in matrix]

    for i in range(len(A)):
        A[i].append(values[i])

    rows = len(A)
    columns = len(A[0]) - 1

    pivot_columns = []
    pivot_row = 0

    for column in range(columns):

        best_row = pivot_row

        for row in range(pivot_row, rows):

            if abs(A[row][column]) > abs(
                A[best_row][column]
            ):
                best_row = row

        if abs(A[best_row][column]) < 1e-9:
            continue

        A[pivot_row], A[best_row] = (
            A[best_row], A[pivot_row]
        )

        divisor = A[pivot_row][column]

        for j in range(column, columns + 1):
            A[pivot_row][j] /= divisor

        for row in range(rows):

            if row == pivot_row:
                continue

            factor = A[row][column]

            for j in range(column, columns + 1):

                A[row][j] -= (
                    factor * A[pivot_row][j]
                )

        pivot_columns.append(column)

        pivot_row += 1

        if pivot_row == rows:
            break

    # Check for inconsistent equations.

    for row in range(rows):

        all_zero = True

        for column in range(columns):

            if abs(A[row][column]) > 1e-8:
                all_zero = False

        if all_zero and abs(A[row][-1]) > 1e-8:
            return None, len(pivot_columns), False

    # Set free variables to zero.

    solution = [0.0 for i in range(columns)]

    for row, column in enumerate(pivot_columns):
        solution[column] = A[row][-1]

    return solution, len(pivot_columns), True


def calculate_mechanism(mechanism):

    log = []
    results = []

    points = mechanism.points
    connections = mechanism.connections
    forces = mechanism.forces

    log.append("MECHANICAL ANALYSIS")
    log.append("\n")

    if len(points) == 0:

        log.append("No points exist.")
        return log, results

    point_indices = {}

    for index, point in enumerate(points):
        point_indices[point.name] = index


    # STEP 1: EXTERNAL FORCES

    external_x = [0.0 for point in points]
    external_y = [0.0 for point in points]

    log.append("")
    log.append("STEP 1: FORCE COMPONENTS")
    log.append("------------------------")

    for force in forces:

        index = point_indices.get(force.point)

        if index is None:
            continue

        radians = math.radians(force.angle)

        fx = force.magnitude * math.cos(radians)
        fy = force.magnitude * math.sin(radians)

        external_x[index] += fx
        external_y[index] += fy

        log.append(
            "Force " + str(force.number) +
            " at point " + force.point
        )

        log.append(
            "Fx = " + str(round(fx, 4)) + " N"
        )

        log.append(
            "Fy = " + str(round(fy, 4)) + " N"
        )

        log.append(
            "Fx = F cos(angle)"
        )

        log.append(
            "Fy = F sin(angle)"
        )

        log.append("")

    # STEP 2: UNKNOWN MEMBER FORCES

    log.append("STEP 2: MEMBER FORCE EQUATIONS")
    log.append("------------------------------")

    unknowns = []

    for connection in connections:

        p1 = find_point(mechanism, connection.point1)
        p2 = find_point(mechanism, connection.point2)

        if p1 is None or p2 is None:
            continue

        dx = p2.x - p1.x
        dy = p2.y - p1.y

        length = math.sqrt(dx ** 2 + dy ** 2)

        if length == 0:
            continue

        unknowns.append({
            "type": "member",
            "name": connection.point1 + "-" + connection.point2,
            "point1": connection.point1,
            "point2": connection.point2,
            "ux": dx / length,
            "uy": dy / length
        })

    # STEP 3: SUPPORT REACTIONS

    log.append("STEP 3: SUPPORT REACTIONS")
    log.append("------------------------")

    for point in points:

        if point.fixed:

            unknowns.append({
                "type": "reaction_x",
                "point": point.name
            })

            unknowns.append({
                "type": "reaction_y",
                "point": point.name
            })

            log.append(
                "Unknown horizontal and vertical "
                "reaction at " + point.name
            )

    # STEP 4: BUILD EQUILIBRIUM EQUATIONS

    log.append("")
    log.append("STEP 4: EQUILIBRIUM EQUATIONS")
    log.append("-----------------------------")

    equation_count = len(points) * 2
    unknown_count = len(unknowns)

    matrix = []

    for i in range(equation_count):
        matrix.append([0.0 for j in range(unknown_count)])

    values = []

    for point in points:

        index = point_indices[point.name]

        values.append(-external_x[index])
        values.append(-external_y[index])

    for column, unknown in enumerate(unknowns):

        if unknown["type"] == "member":

            i = point_indices[unknown["point1"]]
            j = point_indices[unknown["point2"]]

            ux = unknown["ux"]
            uy = unknown["uy"]

            matrix[2 * i][column] += ux
            matrix[2 * i + 1][column] += uy

            matrix[2 * j][column] -= ux
            matrix[2 * j + 1][column] -= uy

        elif unknown["type"] == "reaction_x":

            i = point_indices[unknown["point"]]

            matrix[2 * i][column] = 1.0

        elif unknown["type"] == "reaction_y":

            i = point_indices[unknown["point"]]

            matrix[2 * i + 1][column] = 1.0

    for point in points:

        index = point_indices[point.name]

        log.append(
            "Point " + point.name + ":"
        )

        log.append(
            "Sum Fx = 0; external Fx = " +
            str(round(external_x[index], 4))
        )

        log.append(
            "Sum Fy = 0; external Fy = " +
            str(round(external_y[index], 4))
        )

    # STEP 5: SOLVE EQUATIONS

    log.append("")
    log.append("STEP 5: SOLVING EQUATIONS")
    log.append("-------------------------")

    solution, rank, consistent = solve_linear_system(
        matrix, values
    )

    if not consistent:

        log.append(
            "The equations are inconsistent. "
            "Static equilibrium cannot be established."
        )

        results.append(
            "No equilibrium solution exists for this model."
        )

        return log, results

    if rank < unknown_count:

        log.append(
            "WARNING: The system is underdetermined."
        )

        log.append(
            "There are more unknowns than independent "
            "equations. Some forces cannot be uniquely determined."
        )

        results.append(
            "UNDERDETERMINED: The calculated values are "
            "not a unique solution."
        )

    else:

        log.append(
            "The unknowns have a unique solution."
        )

    # STEP 6: MEMBER FORCES AND SUPPORT REACTIONS

    log.append("")
    log.append("STEP 6: MEMBER FORCES")
    log.append("---------------------")

    member_forces = {}

    for column, unknown in enumerate(unknowns):

        amount = solution[column]

        if unknown["type"] == "member":

            member_forces[unknown["name"]] = amount

            if amount >= 0:
                force_type = "Tension"
            else:
                force_type = "Compression"

            log.append(
                unknown["name"] +
                " = " + str(round(amount, 4)) +
                " N (" + force_type + ")"
            )

            results.append(
                "Beam " + unknown["name"] +
                ": Axial force = " +
                str(round(amount, 4)) +
                " N (" + force_type + ")"
            )

        elif unknown["type"] == "reaction_x":

            log.append(
                "Reaction at " + unknown["point"] +
                " in X = " + str(round(amount, 4)) + " N"
            )

            results.append(
                "Output reaction X at " +
                unknown["point"] + " = " +
                str(round(amount, 4)) + " N"
            )

        elif unknown["type"] == "reaction_y":

            log.append(
                "Reaction at " + unknown["point"] +
                " in Y = " + str(round(amount, 4)) + " N"
            )

            results.append(
                "Output reaction Y at " +
                unknown["point"] + " = " +
                str(round(amount, 4)) + " N"
            )

    # STEP 7: EQUILIBRIUM CHECK

    log.append("")
    log.append("STEP 7: EQUILIBRIUM CHECK")
    log.append("-------------------------")

    for point in points:

        index = point_indices[point.name]

        total_x = external_x[index]
        total_y = external_y[index]

        for column, unknown in enumerate(unknowns):

            amount = solution[column]

            if unknown["type"] == "member":

                if unknown["point1"] == point.name:

                    total_x += amount * unknown["ux"]
                    total_y += amount * unknown["uy"]

                elif unknown["point2"] == point.name:

                    total_x -= amount * unknown["ux"]
                    total_y -= amount * unknown["uy"]

            elif unknown["type"] == "reaction_x":

                if unknown["point"] == point.name:
                    total_x += amount

            elif unknown["type"] == "reaction_y":

                if unknown["point"] == point.name:
                    total_y += amount

        log.append(
            point.name +
            ": Sum Fx = " + str(round(total_x, 6)) +
            " N"
        )

        log.append(
            point.name +
            ": Sum Fy = " + str(round(total_y, 6)) +
            " N"
        )

    # STEP 8: STRESS INFORMATION

    log.append("")
    log.append("STEP 8: BEAM STRESS")
    log.append("-------------------")

    log.append(
        "Stress requires cross-sectional area."
    )

    log.append(
        "Stress = Axial Force / Cross-sectional Area."
    )

    log.append(
        "No beam areas have been supplied, so numerical "
        "stress values cannot yet be calculated."
    )

    for name in member_forces:

        results.append(
            "Beam " + name +
            ": Stress = Not calculated (area required)"
        )

    return log, results

# PAGE DISPLAY HELPERS

def mechanism_display(mechanism):

    return [
        "Name: " + mechanism.name,
        "",
        Pre(create_graph(mechanism)),
        "",
        Pre(create_point_table(mechanism)),
        "",
        Pre(create_force_table(mechanism)),
        ""
    ]


def draft_page(state, message=""):

    mechanism = state.draft

    contents = [
        "CREATE MECHANISM",
        "================",
        "",
        message,
        "",
        "Name:",
        TextBox("mechanism_name", mechanism.name),
        "",
        "ADD POINT",
        Button("Add Point", "draft_add_point"),
        "",
        "ADD FORCE",
        "Point (letter):",
        TextBox("force_point"),
        "Force (Newtons):",
        TextBox("force_magnitude"),
        "Angle (degrees counterclockwise from positive X):",
        TextBox("force_angle"),
        "Fixed Angle (T or F):",
        TextBox("force_fixed_angle", "T"),
        Button("Add Force", "draft_add_force"),
        "",
        "MOVE POINT",
        "Point:",
        TextBox("move_point"),
        "New X:",
        TextBox("move_x"),
        "New Y:",
        TextBox("move_y"),
        Button("Change", "draft_move_point"),
        "",
        "FIX POINT",
        "Point:",
        TextBox("fix_point"),
        Button("Fix", "draft_fix_point"),
        "",
        "ADD CONNECTION",
        "Point 1:",
        TextBox("connect_point_1"),
        "Point 2:",
        TextBox("connect_point_2"),
        Button("Connect", "draft_connect"),
        "",
        "REMOVE CONSTRAINT",
        "Enter a command:",
        "F,Number = Remove Force",
        "P,Letter = Remove Point",
        "C,Letter,Letter = Remove Connection",
        "f,Letter = Remove Fix",
        TextBox("remove_command"),
        Button("Remove", "draft_remove"),
        "",
        "GRAPH",
        Pre(create_graph(mechanism)),
        "",
        Pre(create_point_table(mechanism)),
        "",
        Pre(create_force_table(mechanism)),
        "",
        Button("SAVE MECHANISM", "save_mechanism"),
        Button("Cancel", "view_mechanisms")
    ]

    return Page(state, contents)

# HOME PAGE

@route
def index(state: State) -> Page:

    return Page(state, [
        "MECHANICAL FORCE ANALYZER",
        "\n",
        "",
        "Project Name: " + state.project_name,
        "",
        "Create and analyze two-dimensional mechanical systems.",
        "",
        "Features:",
        "- Add and move points.",
        "- Apply forces at different angles.",
        "- Fix points.",
        "- Connect points.",
        "- View point and force tables.",
        "- Calculate static equilibrium.",
        "- Analyze axial beam forces.",
        "",
        Button("Create Mechanism", "new_mechanism"),
        Button("View Existing Mechanisms", "view_mechanisms")
    ])

# CREATE A NEW MECHANISM

@route
def new_mechanism(state: State) -> Page:

    state.draft = create_empty_mechanism()
    state.editing_index = -1

    return draft_page(state)

# ADD POINT

@route
def draft_add_point(
    state: State,
    mechanism_name: str = "",
    force_point: str = "",
    force_magnitude: str = "",
    force_angle: str = "",
    force_fixed_angle: str = "",
    move_point: str = "",
    move_x: str = "",
    move_y: str = "",
    fix_point: str = "",
    connect_point_1: str = "",
    connect_point_2: str = "",
    remove_command: str = ""
) -> Page:

    mechanism = state.draft

    if mechanism_name.strip() != "":
        mechanism.name = mechanism_name.strip()

    name = next_point_name(mechanism)

    if name is None:
        return draft_page(state, "Maximum of 26 points reached.")

    mechanism.points.append(
        Point(
            name=name,
            x=0,
            y=0,
            fixed=False,
            connections=[]
        )
    )

    update_connections(mechanism)

    return draft_page(
        state,
        "SUCCESS: Point " + name + " added at (0,0)."
    )

# ADD FORCE

@route
def draft_add_force(
    state: State,
    mechanism_name: str = "",
    force_point: str = "",
    force_magnitude: str = "",
    force_angle: str = "",
    force_fixed_angle: str = "",
    move_point: str = "",
    move_x: str = "",
    move_y: str = "",
    fix_point: str = "",
    connect_point_1: str = "",
    connect_point_2: str = "",
    remove_command: str = ""
) -> Page:

    mechanism = state.draft

    point = find_point(mechanism, force_point)

    magnitude = valid_number(force_magnitude)
    angle = valid_number(force_angle)

    fixed_text = force_fixed_angle.strip().upper()

    if point is None:
        return draft_page(state, "ERROR: Point does not exist.")

    if magnitude is None or magnitude < 0:
        return draft_page(state, "ERROR: Enter a valid force.")

    if angle is None:
        return draft_page(state, "ERROR: Enter a valid angle.")

    if fixed_text not in ["T", "F", "TRUE", "FALSE"]:
        return draft_page(state, "Fixed Angle must be T or F.")

    fixed_angle = fixed_text in ["T", "TRUE"]

    mechanism.name = mechanism_name

    number = next_force_number(mechanism)

    mechanism.forces.append(
        Force(
            number,
            point.name,
            magnitude,
            angle,
            fixed_angle
        )
    )

    return draft_page(
        state,
        "Force " + str(number) + " added successfully."
    )

# MOVE POINT

@route
def draft_move_point(
    state: State,
    mechanism_name: str = "",
    force_point: str = "",
    force_magnitude: str = "",
    force_angle: str = "",
    force_fixed_angle: str = "",
    move_point: str = "",
    move_x: str = "",
    move_y: str = "",
    fix_point: str = "",
    connect_point_1: str = "",
    connect_point_2: str = "",
    remove_command: str = ""
) -> Page:

    point = find_point(state.draft, move_point)

    x = valid_number(move_x)
    y = valid_number(move_y)

    if point is None:
        return draft_page(state, "ERROR: Point does not exist.")

    if x is None or y is None:
        return draft_page(state, "ERROR: Enter valid coordinates.")

    if not x.is_integer() or not y.is_integer():
        return draft_page(state, "ERROR: Coordinates must be integers.")

    x = int(x)
    y = int(y)

    if not (-3 <= x <= 3 and -3 <= y <= 3):
        return draft_page(state, "ERROR: Coordinates must be between -3 and 3.")

    point.x = x
    point.y = y

    return draft_page(
        state,
        "Point " + point.name + " moved successfully."
    )

# FIX POINT

@route
def draft_fix_point(
    state: State,
    mechanism_name: str = "",
    force_point: str = "",
    force_magnitude: str = "",
    force_angle: str = "",
    force_fixed_angle: str = "",
    move_point: str = "",
    move_x: str = "",
    move_y: str = "",
    fix_point: str = "",
    connect_point_1: str = "",
    connect_point_2: str = "",
    remove_command: str = ""
) -> Page:

    point = find_point(state.draft, fix_point)

    if point is None:
        return draft_page(state, "ERROR: Point does not exist.")

    point.fixed = True

    return draft_page(
        state,
        "Point " + point.name + " is now fixed."
    )

# CONNECT POINTS

@route
def draft_connect(
    state: State,
    mechanism_name: str = "",
    force_point: str = "",
    force_magnitude: str = "",
    force_angle: str = "",
    force_fixed_angle: str = "",
    move_point: str = "",
    move_x: str = "",
    move_y: str = "",
    fix_point: str = "",
    connect_point_1: str = "",
    connect_point_2: str = "",
    remove_command: str = ""
) -> Page:

    mechanism = state.draft

    p1 = find_point(mechanism, connect_point_1)
    p2 = find_point(mechanism, connect_point_2)

    if p1 is None or p2 is None:
        return draft_page(state, "ERROR: One or both points do not exist.")

    if p1.name == p2.name:
        return draft_page(state, "ERROR: Cannot connect a point to itself.")

    for connection in mechanism.connections:

        if (
            connection.point1 == p1.name
            and connection.point2 == p2.name
        ) or (
            connection.point1 == p2.name
            and connection.point2 == p1.name
        ):
            return draft_page(state, "ERROR: Connection already exists.")

    mechanism.connections.append(
        Connection(p1.name, p2.name)
    )

    update_connections(mechanism)

    return draft_page(
        state,
        "Connected " + p1.name + " to " + p2.name + "."
    )

# REMOVE CONSTRAINT

@route
def draft_remove(
    state: State,
    mechanism_name: str = "",
    force_point: str = "",
    force_magnitude: str = "",
    force_angle: str = "",
    force_fixed_angle: str = "",
    move_point: str = "",
    move_x: str = "",
    move_y: str = "",
    fix_point: str = "",
    connect_point_1: str = "",
    connect_point_2: str = "",
    remove_command: str = ""
) -> Page:

    mechanism = state.draft

    parts = [
        part.strip()
        for part in remove_command.split(",")
    ]

    if len(parts) < 2:
        return draft_page(state, "Invalid removal command.")

    command = parts[0]

    # Remove force: F,1

    if command == "F" and len(parts) == 2:

        number = valid_number(parts[1])

        if number is None or not number.is_integer():
            return draft_page(state, "Invalid force number.")

        number = int(number)

        for force in mechanism.forces:

            if force.number == number:

                mechanism.forces.remove(force)

                return draft_page(
                    state,
                    "Force " + str(number) + " removed."
                )

        return draft_page(state, "Force not found.")

    # Remove point: P,A

    elif command == "P" and len(parts) == 2:

        point = find_point(mechanism, parts[1])

        if point is None:
            return draft_page(state, "Point not found.")

        mechanism.points.remove(point)

        mechanism.forces = [
            force for force in mechanism.forces
            if force.point != point.name
        ]

        mechanism.connections = [
            connection
            for connection in mechanism.connections
            if (
                connection.point1 != point.name
                and connection.point2 != point.name
            )
        ]

        update_connections(mechanism)

        return draft_page(
            state,
            "Point " + point.name + " removed."
        )

    # Remove connection: C,A,B

    elif command == "C" and len(parts) == 3:

        p1 = parts[1].upper()
        p2 = parts[2].upper()

        for connection in mechanism.connections:

            if (
                connection.point1 == p1
                and connection.point2 == p2
            ) or (
                connection.point1 == p2
                and connection.point2 == p1
            ):

                mechanism.connections.remove(connection)

                update_connections(mechanism)

                return draft_page(
                    state,
                    "Connection removed."
                )

        return draft_page(state, "Connection not found.")

    # Remove fixed support: f,A

    elif command == "f" and len(parts) == 2:

        point = find_point(mechanism, parts[1])

        if point is None:
            return draft_page(state, "Point not found.")

        point.fixed = False

        return draft_page(
            state,
            "Fixed constraint removed from " + point.name + "."
        )

    return draft_page(state, "Invalid removal command.")

# SAVE MECHANISM

@route
def save_mechanism(
    state: State,
    mechanism_name: str = "",
    force_point: str = "",
    force_magnitude: str = "",
    force_angle: str = "",
    force_fixed_angle: str = "",
    move_point: str = "",
    move_x: str = "",
    move_y: str = "",
    fix_point: str = "",
    connect_point_1: str = "",
    connect_point_2: str = "",
    remove_command: str = ""
) -> Page:

    name = mechanism_name.strip()

    if name == "":
        return draft_page(state, "ERROR: Give your mechanism a name.")

    if len(state.draft.points) == 0:
        return draft_page(state, "ERROR: Add at least one point.")

    state.draft.name = name

    if state.editing_index == -1:

        state.mechanisms.append(
            copy.deepcopy(state.draft)
        )

    else:

        state.mechanisms[state.editing_index] = (
            copy.deepcopy(state.draft)
        )

    state.editing_index = -1

    return view_mechanisms(state)

# VIEW MECHANISMS

@route
def view_mechanisms(state: State) -> Page:

    contents = [
        "VIEW MECHANISMS",
        "================",
        ""
    ]

    if len(state.mechanisms) == 0:

        contents.append("No saved mechanisms yet.")

    sorted_mechanisms = sorted(
        enumerate(state.mechanisms),
        key=lambda item: item[1].name.lower()
    )

    for index, mechanism in sorted_mechanisms:

        contents.append("")
        contents.append("MECHANISM: " + mechanism.name)

        contents.append(
            "Points: " + str(len(mechanism.points))
        )

        contents.append(
            "Forces: " + str(len(mechanism.forces))
        )

        contents.append(
            "Connections: " + str(len(mechanism.connections))
        )

        contents.append(
            Button(
                "Edit",
                "edit_mechanism",
                [Argument("mechanism_index", index)]
            )
        )

        contents.append(
            Button(
                "Details",
                "select_details",
                [Argument("mechanism_index", index)]
            )
        )

        contents.append(
            Button(
                "Calculations",
                "select_calculations",
                [Argument("mechanism_index", index)]
            )
        )

        contents.append(
            Button(
                "Results",
                "select_results",
                [Argument("mechanism_index", index)]
            )
        )

        contents.append(
            Button(
                "Delete",
                "delete_mechanism",
                [Argument("mechanism_index", index)]
            )
        )

        contents.append("---------------------------")

    contents.append(
        Button("Create New Mechanism", "new_mechanism")
    )

    contents.append(
        Button("Home", "index")
    )

    return Page(state, contents)

# EDIT MECHANISM

@route
def edit_mechanism(
    state: State,
    mechanism_index: int
) -> Page:

    if not (0 <= mechanism_index < len(state.mechanisms)):
        return view_mechanisms(state)

    state.editing_index = mechanism_index

    state.draft = copy.deepcopy(
        state.mechanisms[mechanism_index]
    )

    return draft_page(
        state,
        "Editing: " + state.draft.name
    )

# DELETE MECHANISM

@route
def delete_mechanism(
    state: State,
    mechanism_index: int
) -> Page:

    if 0 <= mechanism_index < len(state.mechanisms):

        state.mechanisms.pop(mechanism_index)

    state.selected_index = -1

    return view_mechanisms(state)

# SELECT MECHANISM FOR DETAILS

@route
def select_details(
    state: State,
    mechanism_index: int
) -> Page:

    if 0 <= mechanism_index < len(state.mechanisms):

        state.selected_index = mechanism_index

    return details(state)

# DETAILS PAGE

@route
def details(state: State) -> Page:

    if not (
        0 <= state.selected_index < len(state.mechanisms)
    ):

        return view_mechanisms(state)

    mechanism = state.mechanisms[state.selected_index]

    contents = [
        "MECHANISM DETAILS",
        "=================",
        ""
    ]

    contents += mechanism_display(mechanism)

    contents += [
        Button("View Mechanisms", "view_mechanisms"),

        Button(
            "Edit",
            "edit_mechanism",
            [Argument("mechanism_index", state.selected_index)]
        ),

        Button(
            "Calculations",
            "select_calculations",
            [Argument("mechanism_index", state.selected_index)]
        ),

        Button(
            "Results",
            "select_results",
            [Argument("mechanism_index", state.selected_index)]
        )
    ]

    return Page(state, contents)

# CALCULATIONS PAGE

@route
def select_calculations(
    state: State,
    mechanism_index: int
) -> Page:

    if not (0 <= mechanism_index < len(state.mechanisms)):
        return view_mechanisms(state)

    state.selected_index = mechanism_index

    mechanism = state.mechanisms[mechanism_index]

    state.calculations_log, state.results = (
        calculate_mechanism(mechanism)
    )

    return calculations(state)


@route
def calculations(state: State) -> Page:

    if not (
        0 <= state.selected_index < len(state.mechanisms)
    ):
        return view_mechanisms(state)

    mechanism = state.mechanisms[state.selected_index]

    contents = [
        "CALCULATIONS",
        "============",
        "",
        "Mechanism: " + mechanism.name,
        "",
        Pre("\n".join(state.calculations_log)),
        "",
        Button("Results", "results"),
        Button("View Mechanisms", "view_mechanisms"),
        Button("Details", "details")
    ]

    return Page(state, contents)

# SELECT RESULTS

@route
def select_results(
    state: State,
    mechanism_index: int
) -> Page:

    if not (0 <= mechanism_index < len(state.mechanisms)):
        return view_mechanisms(state)

    state.selected_index = mechanism_index

    mechanism = state.mechanisms[mechanism_index]

    state.calculations_log, state.results = (
        calculate_mechanism(mechanism)
    )

    return results(state)

# RESULTS PAGE

@route
def results(state: State) -> Page:

    if not (
        0 <= state.selected_index < len(state.mechanisms)
    ):
        return view_mechanisms(state)

    mechanism = state.mechanisms[state.selected_index]

    contents = [
        "MECHANISM RESULTS",
        "=================",
        "",
        "Mechanism: " + mechanism.name,
        "",
        "BEAM FORCES AND SUPPORT REACTIONS",
        "---------------------------------",
        ""
    ]

    for result in state.results:
        contents.append(result)

    contents += [
        "",
        "EXTERNAL FORCE INFORMATION",
        "--------------------------",
        ""
    ]

    for force in mechanism.forces:

        fx = force.magnitude * math.cos(
            math.radians(force.angle)
        )

        fy = force.magnitude * math.sin(
            math.radians(force.angle)
        )

        contents.append(
            "Force " + str(force.number) +
            " at " + force.point
        )

        contents.append(
            "X Component: " + str(round(fx, 4)) + " N"
        )

        contents.append(
            "Y Component: " + str(round(fy, 4)) + " N"
        )

        contents.append("")

    contents += [
        "STRESS INFORMATION",
        "-------------------",
        "",
        "Numerical beam stress requires cross-sectional area.",
        "This version reports axial member forces, not "
        "verified material stress or structural safety.",
        "",
        Button("View Calculations", "calculations"),
        Button("View Mechanisms", "view_mechanisms"),
        Button("Details", "details")
    ]

    return Page(state, contents)

# START SERVER

start_server(
    State(
        [],
        create_empty_mechanism(),
        -1,
        -1,
        [],
        [],
        "Mechanical Force Analyzer"
    )
)

