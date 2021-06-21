import numpy as np
import copy

class Evaluate:
    def __init__(self, w):
        #self.w = np.random.normal(0, 0.5,156)
        #self.x = np.random.normal(0, 0.5,156)
        self.w = w
        self.x = np.zeros(150)
        self.x1 = np.zeros(150)
        self.x2 = np.zeros(150)
        self.eta = 0.25
        self.arrangement = self.create_arrangement()

    def create_arrangement(self):
        p = [(1,2,3),(2,1,3),(3,1,2),
             (1,2,0),(2,1,0),(1,3,0),
             (3,1,0),(2,3,0),(3,2,0),
             (1,0,0),(2,0,0),(3,0,0)]
        q = [(4,5,6),(5,4,6),(6,4,5),
             (4,5,0),(5,4,0),(4,6,0),
             (6,4,0),(5,6,0),(6,5,0),
             (4,0,0),(5,0,0),(6,0,0)]
        arrangement = []
        for i in p:
            for j in q:
                arrangement.append(i+j)
        return arrangement


    def evaluate(self, who, gamestate, child):
        my_team = gamestate.get_team(who)
        opp_team = gamestate.get_team(1 - who)
        i = 0
        #自分ポケモン情報
        for p in my_team.poke_list:
            self.x[i] = p.health/p.final_stats['hp']
            i += 1
            """
            if p.alive:
                self.x[i] = 1
            else:
                self.x[i] = 0
            i += 1
            """
            """
            self.x[i] = p.stages["patk"]/6
            i += 1
            self.x[i] = p.stages["spatk"]/6
            i += 1
            self.x[i] = p.stages["pdef"]/6
            i += 1
            self.x[i] = p.stages["spdef"]/6
            i += 1
            self.x[i] = p.stages["spe"]/6
            i += 1
            """
        #相手ポケモン情報
        for p in opp_team.poke_list:
            self.x[i] = p.health/p.final_stats['hp']
            i += 1
            """
            if p.alive:
                self.x[i] = 1
            else:
                self.x[i] = 0
            i += 1
            """
            """
            self.x[i] = p.stages["patk"]/6
            i += 1
            self.x[i] = p.stages["spatk"]/6
            i += 1
            self.x[i] = p.stages["pdef"]/6
            i += 1
            self.x[i] = p.stages["spdef"]/6
            i += 1
            self.x[i] = p.stages["spe"]/6
            i += 1
            if p.alive:
                self.x[i] = 1000
            else:
                self.x[i] = 1000
            i += 1
            """
        #配置パターン
        choice1 = [my_team.primary_poke+1]
        choice2 = [opp_team.primary_poke+4]
        for i in range(3):
            if i != my_team.primary_poke and my_team[i].alive:
                choice1.append(i+1)
            if i != opp_team.primary_poke and opp_team[i].alive:
                choice2.append(i+4)
        for i in range(2):
            if len(choice1) < 3:
                choice1.append(0)
            if len(choice2) < 3:
                choice2.append(0)
        choice = choice1 + choice2
        choice = tuple(choice)
        for i in range(144):
            if choice == self.arrangement[i]:
                self.x[i+6] = 1
            else:
                self.x[i+6] = 0


        """
        #対面パターン

        for m in range(3):
            for n in range(3):
                if my_team.primary_poke == m and opp_team.primary_poke == n:
                    self.x[i] = 1
                else:
                    self.x[i] = 0
                i += 1
        """
        if child:
            self.x1 = self.x.copy()
        win_bonus = 0
        if gamestate.is_over():
            if my_team.alive():
                win_bonus = 10000
            else:
                win_bonus = -10000

        return np.dot(self.w ,self.x) + win_bonus

    def convert_winning_rate(self,evaluate):
        v = evaluate
        return 1/(1+np.exp((-1)*v))

    def zoukin(self, evaluate1, evaluate2):#evaluate1...t , evaluate2...t+1
        p1 = self.convert_winning_rate(evaluate1)
        p2 = self.convert_winning_rate(evaluate2)
        self.w = self.w + self.eta * (p2 - p1) * p1 * (1 - p1) * self.x1
