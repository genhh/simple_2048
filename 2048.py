#-*- coding:utf-8 -*-
#curses库报错，安装第三方库即可 pip install  xxx.whl
import random
import curses
from itertools import chain
from collections import defaultdict
import logging
import copy
logger = logging.getLogger(__name__)
logger.setLevel(level = logging.INFO)
handler = logging.FileHandler("log.txt",'w')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

#global allhighscore
#allhighscore =0
#获取用户action
class Action(object):

    UP = 'up'
    LEFT = 'left'
    DOWN = 'down'
    RIGHT = 'right'
    RESTART = 'restart'
    EXIT = 'exit'

    letter_codes = [ord(ch) for ch in 'WASDRQwasdrq']
    actions = [UP, LEFT, DOWN, RIGHT, RESTART, EXIT]
    actions_dict = dict(zip(letter_codes, actions * 2))

    def __init__(self, stdscr):
        self.stdscr = stdscr

    def get(self):
        char = "N"
        while char not in self.actions_dict:
            char = self.stdscr.getch()
        return self.actions_dict[char]


class Grid(object):

    def __init__(self, size):
        self.size = size
        self.cells = None
        self.score = 0
        self.highscore = 0
        self.reset()

    def reset(self):
        
        #logger.info("grid:self.highscore  %s" % self.highscore)
        self.cells = [[0 for i in range(self.size)] for j in range(self.size)]
        self.add_random_item()
        self.add_random_item()

    def add_random_item(self):
        empty_cells = [(i, j) for i in range(self.size) for j in range(self.size) if self.cells[i][j] == 0]
        (i, j) = random.choice(empty_cells)
        self.cells[i][j] = 4 if random.randrange(100) >= 90 else 2

    def transpose(self):
        self.cells = [list(row) for row in zip(*self.cells)]

    def invert(self):
        self.cells = [row[::-1] for row in self.cells]

    #@staticmethod ：名义上是类的函数，但是不能调用和访问类属性、实例属性
    
    def move_row_left(self,row):
        def tighten(row):
            new_row = [i for i in row if i != 0]
            new_row += [0 for i in range(len(row) - len(new_row))]
            return new_row

        def merge(row):
            pair = False
            new_row = []
            for i in range(len(row)):
                if pair:
                    new_row.append(2 * row[i])
                    self.score += 2 * row[i]
                    pair = False
                else:
                    if i + 1 < len(row) and row[i] == row[i + 1]:
                        pair = True
                        new_row.append(0)
                    else:
                        new_row.append(row[i])
            assert len(new_row) == len(row)
            return new_row
        return tighten(merge(tighten(row)))

    def move_left(self):
        self.cells = [self.move_row_left(row) for row in self.cells]

    def move_right(self):
        self.invert()
        self.move_left()
        self.invert()

    def move_up(self):
        self.transpose()
        self.move_left()
        self.transpose()

    def move_down(self):
        self.transpose()
        self.move_right()
        self.transpose()

    @staticmethod
    def row_can_move_left(row):
        def change(i):
            if row[i] == 0 and row[i + 1] != 0:
                return True
            if row[i] != 0 and row[i + 1] == row[i]:
                return True
            return False
        return any(change(i) for i in range(len(row) - 1))

    def can_move_left(self):
        return any(self.row_can_move_left(row) for row in self.cells)

    def can_move_right(self):
        self.invert()
        can = self.can_move_left()
        self.invert()
        return can

    def can_move_up(self):
        self.transpose()
        can = self.can_move_left()
        self.transpose()
        return can

    def can_move_down(self):
        self.transpose()
        can = self.can_move_right()
        self.transpose()
        return can


class Screen(object):

    help_string1 = '(W)up (S)down (A)left (D)right'
    help_string2 = '     (R)Restart (Q)Exit'
    over_string = '           GAME OVER'
    win_string = '          YOU WIN!'

    def __init__(self, highscore = 0,screen=None, grid=None, score=0,best_score=0, over=False, win=False):
        self.grid = grid
        self.score = score
        self.highscore = highscore
        self.over = over
        self.win = win
        self.screen = screen
        self.counter = 0

    def cast(self, string):
        self.screen.addstr(string + '\n')

    def draw_row(self, row):
        self.cast(''.join('|{: ^5}'.format(num) if num > 0 else '|     ' for num in row) + '|')

    def draw(self):
        self.screen.clear()
        self.score = self.grid.score
        if self.score > self.highscore:
            self.highscore = self.score
        
        self.cast('SCORE: ' + str(self.score))
        self.cast('HighSCORE: ' + str(self.highscore))
        for row in self.grid.cells:
            self.cast('+-----' * self.grid.size + '+')
            self.draw_row(row)
        self.cast('+-----' * self.grid.size + '+')

        if self.win:
            self.cast(self.win_string)
        else:
            if self.over:
                self.cast(self.over_string)
            else:
                self.cast(self.help_string1)

        self.cast(self.help_string2)
        return self.highscore


class GameManager(object):

    def __init__(self, size=4, win_num=64):
        self.size = size
        self.win_num = win_num
        #logger.info("GameManager:__init__:highscore  %s" % self.screen.highscore)
        self.score_store = 0
        self.reset()

    def reset(self):
        self.state = 'init'
        self.win = False
        self.over = False
        self.score = 0
        #logger.info("GameManager:reset:highscore  %s" % self.screen.highscore)
        self.grid = Grid(self.size)
        
        #print(self.screen.highscore)
        self.grid.reset()

    @property
    def screen(self):
        #logger.info("GameManager:screen:highscore  %s" % self.screen.highscore)
        return Screen(highscore= self.score_store,screen=self.stdscr, score=self.score, grid=self.grid, win=self.win, over=self.over)

    def move(self, direction):
        logger.info("GameManager:move:highscore  %s" % self.screen.highscore)
        if self.can_move(direction):
            getattr(self.grid, 'move_' + direction)()
            self.grid.add_random_item()
            return True
        else:
            return False

    @property
    def is_win(self):
        logger.info("GameManager:is_win:highscore  %s" % self.screen.highscore)
        self.win = max(chain(*self.grid.cells)) >= self.win_num
        return self.win

    @property
    def is_over(self):
        logger.info("GameManager:is_over:highscore  %s" % self.screen.highscore)
        self.over = not any(self.can_move(move) for move in self.action.actions)
        return self.over

    def can_move(self, direction):
        logger.info("GameManager:can_move:highscore  %s" % self.screen.highscore)
        return getattr(self.grid, 'can_move_' + direction)()

    def state_init(self):
        logger.info("Screen:state_init:highscore  %s" % self.screen.highscore)
        
        self.reset()
        return 'game'

    def state_game(self):
        self.score_store = self.screen.draw()
        action = self.action.get()

        if action == Action.RESTART:
            
            return 'init'
        if action == Action.EXIT:
            return 'exit'
        if self.move(action):
            if self.is_win:
                return 'win'
            if self.is_over:
                return 'over'
        return 'game'

    def _restart_or_exit(self):
        #logger.info("GameManager:_restart_or_exit:highscore  %s" % self.screen.highscore)
        self.score_store = self.screen.draw()
        return 'init' if self.action.get() == Action.RESTART else 'exit'

    def state_win(self):
        logger.info("GameManager:state_win:highscore  %s" % self.screen.highscore)
        return self._restart_or_exit()

    def state_over(self):
        logger.info("GameManager:state_over:highscore  %s" % self.screen.highscore)
        return self._restart_or_exit()

    #类似于在类中重载 () 运算符，可以使类实例以调用普通函数那样进行调用："对象名()"
    def __call__(self, stdscr):
        curses.use_default_colors()
        self.stdscr = stdscr
        self.action = Action(stdscr)
        i=0
        while self.state != 'exit':
            logger.info("GameManager:__call__:highscore  %s" % self.screen.highscore)
            self.state = getattr(self, 'state_' + self.state)()
            i = i+1



"""
#全局变量
actions = ['Up', 'Left', 'Down', 'Right', 'Restart', 'Exit']
letter_codes = [ord(ch) for ch in 'WASDRQwasdrq']
actions_dict = dict(zip(letter_codes, actions * 2))
#用户输入处理
def get_user_action(keyboard):
    char = "N"
    while char not in actions_dict:
        char = keyboard.getch()
    return actions_dict[char]

    pass

#矩阵转置
def transpose(field):
    return [list(row) for row in zip(*field)]

#逆序矩阵
def invert(field):
    return [row[::-1] for row in field]

class GameField(object):
    def __init__(self,height=4, width=4, win=2048):
        self.height = height       # 高
        self.width = width         # 宽
        self.win_value = 2048      # 过关分数
        self.score = 0             # 当前分数
        self.highscore = 0         # 最高分
        self.reset()               # 棋盘重置
    
    #随机生成数字
    def spawn(self):
        # 从 100 中取一个随机数，如果这个随机数大于 89，new_element 等于 4，否则等于 2
        new_element = 4 if random.randrange(100) > 89 else 2
        # 得到一个随机空白位置的元组坐标
        (i,j) = random.choice([(i,j) for i in range(self.width) for j in range(self.height) if self.field[i][j] == 0]) #choice:从序列中随机选择一个
        self.field[i][j] = new_element

    #重置棋盘
    def reset(self):
        # 更新分数
        if self.score > self.highscore:
            self.highscore = self.score
        self.score = 0
        # 初始化游戏开始界面
        self.field = [[0 for i in range(self.width)] for j in range(self.height)]
        self.spawn()
        self.spawn()
        
    #元素移动
    def move(self,direction):
        def move_row_left(row):
            def tighten(row):
                '''把零散的非零单元挤到一块'''
                # 先将非零的元素全拿出来加入到新列表
                new_row = [i for i in row if i != 0]
                # 按照原列表的大小，给新列表后面补零
                new_row += [0 for i in range(len(row) - len(new_row))]
                return new_row

            def merge(row):
                '''对邻近元素进行合并'''
                pair = False
                new_row = []
                for i in range(len(row)):
                    if pair:
                        # 合并后，加入乘 2 后的元素在 0 元素后面
                        new_row.append(2 * row[i])
                        # 更新分数
                        self.score += 2 * row[i]
                        pair = False
                    else:
                        # 判断邻近元素能否合并
                        if i + 1 < len(row) and row[i] == row[i + 1]:
                            pair = True
                            # 可以合并时，新列表加入元素 0
                            new_row.append(0)
                        else:
                            # 不能合并，新列表中加入该元素
                            new_row.append(row[i])
                # 断言合并后不会改变行列大小，否则报错
                assert len(new_row) == len(row)
                return new_row
            # 先挤到一块再合并再挤到一块
            return tighten(merge(tighten(row)))
        # 创建 moves 字典，把不同的棋盘操作作为不同的 key，对应不同的方法函数
        moves = {}
        moves['Left']  = lambda field: [move_row_left(row) for row in field]
        moves['Right'] = lambda field: invert(moves['Left'](invert(field)))
        moves['Up']    = lambda field: transpose(moves['Left'](transpose(field)))
        moves['Down']  = lambda field: transpose(moves['Right'](transpose(field)))
        # 判断棋盘操作是否存在且可行
        if direction in moves:
            if self.move_is_possible(direction):
                self.field = moves[direction](self.field)
                self.spawn()
                return True
            else:
                return False
        
    #判断输赢
    def is_win(self):
        # 任意一个位置的数大于设定的 win 值时，游戏胜利
        return any(any(i >= self.win_value for i in row) for row in self.field)
        
    def is_gameover(self):
        return not any(self.move_is_possible(move) for move in actions)
    
    #判断能否移动
    def move_is_possible(self,direction):
        def row_is_left_movable(row):
            '''判断一行里面能否有元素进行左移动或合并
            '''
            def change(i):
                # 当左边有空位（0），右边有数字时，可以向左移动
                if row[i] == 0 and row[i + 1] != 0:
                    return True
                # 当左边有一个数和右边的数相等时，可以向左合并
                if row[i] != 0 and row[i + 1] == row[i]:
                    return True
                return False
            return any(change(i) for i in range(len(row) - 1))

        # 检查能否移动（合并也可以看作是在移动）
        check = {}
        # 判断矩阵每一行有没有可以左移动的元素
        check['Left']  = lambda field: any(row_is_left_movable(row) for row in field)
        # 判断矩阵每一行有没有可以右移动的元素。这里只用进行判断，所以矩阵变换之后，不用再变换复原
        check['Right'] = lambda field: check['Left'](invert(field))

        check['Up']    = lambda field: check['Left'](transpose(field))

        check['Down']  = lambda field: check['Right'](transpose(field))

        # 如果 direction 是“左右上下”即字典 check 中存在的操作，那就执行它对应的函数
        if direction in check:
            # 传入矩阵，执行对应函数
            return check[direction](self.field)
        else:
            return False    

    #绘制游戏界面
    def draw(self, screen):
        help_string1 = '(W)Up (S)Down (A)Left (D)Right'
        help_string2 = '     (R)Restart (Q)Exit'
        gameover_string = '           GAME OVER'
        win_string = '          YOU WIN!'

        # 绘制函数
        def cast(string):
            # addstr() 方法将传入的内容展示到终端!
            screen.addstr(string + '\n')

        # 绘制水平分割线的函数
        def draw_hor_separator():
            line = '+' + ('+------' * self.width + '+')[1:]
            cast(line)

        # 绘制竖直分割线的函数
        def draw_row(row):
            cast(''.join('|{: ^5} '.format(num) if num > 0 else '|      ' for num in row) + '|')

        # 清空屏幕
        screen.clear()
        # 绘制分数和最高分
        cast('SCORE: ' + str(self.score))
        if 0 != self.highscore:
            cast('HIGHSCORE: ' + str(self.highscore))

        # 绘制行列边框分割线
        for row in self.field:
            draw_hor_separator()
            draw_row(row)
        draw_hor_separator()

        # 绘制提示文字
        if self.is_win():
            cast(win_string)
        else:
            if self.is_gameover():
                cast(gameover_string)
            else:
                cast(help_string1)
        cast(help_string2)


#主逻辑函数(状态循环)
def main(stdscr):
    def init():
        game_field.reset()
        return "Game"

    #游戏结束时的状态
    def not_game(state):
        # 根据状态画出游戏的界面
        game_field.draw(stdscr)
        # 读取用户输入得到 action，判断是重启游戏还是结束游戏
        action = get_user_action(stdscr)
        # 如果没有 'Restart' 和 'Exit' 的 action，将一直保持现有状态
        responses = defaultdict(lambda : state) #输入一个函数，当试图访问不存在的key时就会调用此函数生成key以及通过此函数生成的value，而不是报错
        responses['Restart'], responses['Exit'] = 'Init', 'Exit'
        return responses[action]

    #游戏进行时
    def game():
        # 根据状态画出游戏的界面
        game_field.draw(stdscr) #实例名称
        # 读取用户输入得到 action
        action = get_user_action(stdscr)
        if action == 'Restart':
            return 'Init'
        if action == 'Exit':
            return 'Exit'
        if game_field.move(action):  # move successful
            if game_field.is_win():
                return 'Win'
            if game_field.is_gameover():
                return 'Gameover'
        #if 成功移动:
        # if 游戏胜利:
        # if 游戏失败:
        return 'Game'
    # 使用颜色配置默认值
    curses.use_default_colors()
    
    game_field = GameField(win=2048)

    #函数转换
    state_actions = {
        'Init': init,
        'Win': lambda:not_game('Win'),
        'Gameover':lambda: not_game('Gameover'),
        'Game': game
    }
    state = 'Init'

    #开始循环
    while state != 'Exit':
        state = state_actions[state]()
"""





if __name__ == '__main__':
    #curses.wrapper(main)
    #gameman = 
    curses.wrapper(GameManager())

