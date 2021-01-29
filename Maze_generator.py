import random


def get_chance(chance):
    if random.random() < chance:
        return True
    return False


def generate(width, height, seed=None):
    if seed is not None:
        random.seed(seed)
    chance = 0.4
    lab_width = random.randint(6, 9)
    lab_height = random.randint(5, 6)
    # wall_length = min(int(width / lab_width), int(height / lab_height))
    wall_length = 120
    walls = []
    maze = []
    for i in range(lab_height):
        maze.append([])
    # стена описывается кортежем (X, Y, угол поворота)
    # создание "рамок"
    for i in range(lab_width):
        walls.append([(i + 0.5) * wall_length, 0, 90])
        walls.append([(i + 0.5) * wall_length, lab_height * wall_length, 90])
    for i in range(lab_height):
        walls.append([0, (i + 0.5) * wall_length, 0])
        walls.append([lab_width * wall_length, (i + 0.5) * wall_length, 0])
    # создание лабиринта по множествам
    # первая строка
    for i in range(1, lab_width + 1):
        maze[0].append(i)
    for i in range(lab_width - 1):
        if get_chance(0.6):
            maze[0][i + 1] = maze[0][i]
        else:
            walls.append([(i + 1) * wall_length, 0.5 * wall_length, 0])
    maze_string = {}
    for i in range(lab_width):
        if maze[0][i] not in maze_string:
            maze_string[maze[0][i]] = 1
        else:
            maze_string[maze[0][i]] += 1
    hor_walls = []
    for i in range(lab_width):
        if maze_string[maze[0][i]] != 1:
            if get_chance(chance):
                hor_walls.append(i)
                walls.append([(i + 0.5) * wall_length, 1 * wall_length, 90])

    for j in range(1, lab_height - 1):  # центральные строки
        for i in range(lab_width):
            if i not in hor_walls:
                maze[j].append(maze[j - 1][i])
            else:
                maze[j].append(0)
        for i in range(lab_width):
            if maze[j][i] == 0:
                k = 1
                while k in maze[j]:
                    k += 1
                maze[j][i] = k
        for i in range(lab_width - 1):
            if get_chance(chance):
                maze[j][i + 1] = maze[j][i]
            else:
                walls.append([(i + 1) * wall_length, (j + 0.5) * wall_length, 0])
        maze_string = {}
        for i in range(lab_width):
            if maze[j][i] not in maze_string:
                maze_string[maze[j][i]] = 1
            else:
                maze_string[maze[j][i]] += 1
        hor_walls = []
        for i in range(lab_width):
            if maze_string[maze[j][i]] > 1:
                if get_chance(chance):
                    hor_walls.append(i)
                    walls.append([(i + 0.5) * wall_length, (j + 1) * wall_length, 90])
                    maze_string[maze[j][i]] -= 1

    for i in range(lab_width):  # последняя строка
        if i in hor_walls:
            maze[-1].append(0)
        else:
            maze[-1].append(maze[-2][i])
    for j in range(lab_width):
        if maze[-1][j] == 0:
            k = 1
            while k in maze[-1]:
                k += 1
            maze[-1][j] = k
    for i in range(1, lab_width):
        if maze[-1][i] == maze[-1][i - 1]:
            walls.append([i * wall_length, (lab_height - 0.5) * wall_length, 0])

    return walls, wall_length, (lab_width, lab_height)
