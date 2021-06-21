from simulator import Simulator, Action
import random
import logging
import time

import numpy as np
logging.basicConfig()

class Agent():

    def get_action(self, gamestate, who):
        raise NotImplementedError()

#死んだときに交代する機能を付ける
class HumanAgent(Agent):

    def get_action(self, gamestate, who):
        valid = False
        my_team = gamestate.get_team(who) #自分のチームの取得
        print("My moves:", [m for m in my_team.primary().moveset.moves]) #技一覧
        print("My switches:", [(m, i) for i, m in enumerate(my_team.poke_list) if m != my_team.primary() and m.alive]) #交代一覧
        my_legal = gamestate.get_legal_actions(who, log=True) #できる行動
        while not valid:
            action_string = input('> ') #raw_inputはコンソールからのinput
            try:
                my_action = Action.create(action_string)
                if my_action not in my_legal:
                    print("Illegal move", my_action, my_legal)
                    assert False
                valid = True
            except:
                print('miss')
                pass
        return my_action


class MinimaxAgent(Agent):
    #opp_actionがたまにNoneになってerrorになる
    def __init__(self, depth, pokedata, evaluate, use_cache=False, alphabet=False, log_file=None):
        self.depth = depth
        self.evaluate = evaluate
        self.simulator = Simulator(pokedata)
        self.cache = {}
        self.hit_count = 0
        self.prune_count = 0
        self.use_cache = use_cache
        self.alphabet = alphabet
        self.log_file = log_file

    def get_random_action(self,state, who):
        my_legal_actions = state.get_legal_actions(who)
        action = random.choice(my_legal_actions)
        return action

    def get_action(self, state, who, log=True):
        """
        start = time.time()

        my_legal_actions = state.get_legal_actions(who)
        print("my_legal_actions",my_legal_actions)
        opp_legal_actions = state.get_legal_actions(1 - who)
        print('opp_legal_actions',opp_legal_actions)
        """
        best_action, value, opp_action = self.minimax(state, self.depth, who, log=log)
        """
        end = time.time()
        elapsed = end - start
        print("time:",elapsed)

        if self.log_file is not None:
            with open(self.log_file, 'a') as fp:
                print >>fp, elapsed
        """
        if best_action:
            if best_action.is_move():
                my_move_name = state.get_team(who).primary().moveset.moves[best_action.move_index]
            if opp_action.is_move():
                opp_move_name = state.get_team(1 - who).primary().moveset.moves[opp_action.move_index]
            if best_action.is_switch():
                my_move_name = "Switch[%s]" % state.get_team(who).poke_list[best_action.switch_index]
            if opp_action.is_switch():
                opp_move_name = "Switch[%s]" % state.get_team(1 - who).poke_list[opp_action.switch_index]
            if log:
                print("I think you are going to use %s(%s, %s, %s) and I will use %s(%s, %s, %s)." % (
                    opp_move_name, opp_action.backup_switch, opp_action.mega, opp_action.volt_turn,
                    my_move_name, best_action.backup_switch, best_action.mega, best_action.volt_turn,
                ))

        return best_action
    #両方死んだときに対応していない
    def get_dead_switch(self, state, who, log=False):
        my_team = state.teams[who]
        if my_team.primary().alive:
            return None
        pokemon = range(len(my_team.poke_list))
        valid_switches = [i for i in pokemon if my_team.poke_list[i].alive and i != my_team.primary_poke]
        my_v = float('-inf')
        best_switch = None
        for switch in valid_switches:
            state.switch_pokemon(switch, who)
            best_action, value, opp_action = self.minimax(state, self.depth, who, log=log)
            if my_v < value:
                my_v = value
                best_switch = switch
        return best_switch #return int

class PessimisticMinimaxAgent(MinimaxAgent):

    def minimax(self, state, depth, who, log=False, learn=True):
        if state.is_over() or depth == 0:
            if who == 0:
                return None, self.evaluate.evaluate(who, state, False), None
            else:
                return None, state.evaluate2(who), None
        my_legal_actions = state.get_legal_actions(who)
        #print(my_legal_actions)
        opp_legal_actions = state.get_legal_actions(1 - who)
        my_v = float('-inf')
        best_action = None
        best_best_opp_action = None
        actions = [None, None]
        for my_action in my_legal_actions:
            opp_v = float("inf")
            best_opp_action = None
            actions[who] = my_action
            for opp_action in opp_legal_actions:
                actions[1 - who] = opp_action
                new_state = self.simulator.simulate(state, actions, who)
                
                #ポケモンが死んだとき(あとできれいにする)(これだと両方同時に死んだ場合に対処できない)
                #自分のポケモンが死んだとき
                if not new_state.teams[who].primary().alive:
                    pokemon = range(len(new_state.teams[who].poke_list))
                    valid_switches = [i for i in pokemon if new_state.teams[who].poke_list[who].alive and i != new_state.teams[who].primary_poke]
                    #交代先がいるとき
                    if valid_switches != []:
                        for poke in valid_switches:
                            new_state.switch_pokemon(poke, who)
                            new_action, state_value, _ = self.minimax(new_state, depth-1, who)
                            if opp_v >= state_value:
                                opp_v = state_value
                                best_opp_action = opp_action
                    #交代できないとき　交代先がいないとき
                    else:
                        new_action, state_value, _ = self.minimax(new_state, depth-1, who)
                        if opp_v >= state_value:
                            opp_v = state_value
                            best_opp_action = opp_action

                #相手のポケモンが死んだとき
                elif not new_state.teams[1-who].primary().alive:
                    pokemon = range(len(new_state.teams[1-who].poke_list))
                    valid_switches = [i for i in pokemon if new_state.teams[1-who].poke_list[i].alive and i != new_state.teams[1-who].primary_poke]
                    #交代先がいるとき
                    if valid_switches != []:
                        for poke in valid_switches:
                            new_state.switch_pokemon(poke, 1-who)
                            new_action, state_value, _ = self.minimax(new_state, depth-1, who)
                            if opp_v >= state_value:
                                opp_v = state_value
                                best_opp_action = opp_action
                    #交代できないとき　交代先がいないとき
                    else:
                        new_action, state_value, _ = self.minimax(new_state, depth-1, who)
                        if opp_v >= state_value:
                            opp_v = state_value
                            best_opp_action = opp_action

                #誰も死んでないとき
                else:
                    new_action, state_value, _ = self.minimax(new_state, depth-1, who)
                    if opp_v >= state_value:
                        opp_v = state_value
                        best_opp_action = opp_action

            if opp_v > my_v:
                best_action = my_action
                best_best_opp_action = best_opp_action
                my_v = opp_v
        return best_action, my_v, best_best_opp_action

class OptimisticMinimaxAgent(MinimaxAgent):

    def minimax(self, state, depth, who, log=False):
        if state.is_over() or depth == 0:
            return None, state.evaluate(who), None
        my_legal_actions = state.get_legal_actions(who)
        opp_legal_actions = state.get_legal_actions(1 - who)
        opp_v = float('inf')
        best_action = None
        best_best_my_action = None
        actions = [None, None]
        for opp_action in opp_legal_actions:
            my_v = float("-inf")
            best_my_action = None
            actions[1 - who] = opp_action
            for my_action in my_legal_actions:
                actions[who] = my_action
                new_state = self.simulator.simulate(state, actions, who)
                tuple_state = new_state.to_tuple()
                if (depth, tuple_state) in self.cache:
                    new_action, state_value = self.cache[(depth, tuple_state)]
                    self.hit_count += 1
                else:
                    new_action, state_value, _ = self.minimax(new_state, depth - 1, who)
                    self.cache[(depth, tuple_state)] = (my_action, state_value)
                if my_v < state_value:
                    my_v = state_value
                    best_my_action = my_action
                if state_value > opp_v:
                    self.prune_count += 1
                    break
            if my_v < opp_v:
                best_action = opp_action
                best_best_my_action = best_my_action
                opp_v = my_v
        return best_best_my_action, opp_v, best_action


'''
class Reinforce:
    GAMMA = 0.99
    ETA = 0.5
    MAX_STEPS = 200
    NUM_EPISODES = 1000
    num_state = 6
    num_actions = 6
    NUM_DIZITIZED = 6

    class Agent:
        def __init__(self, num_states, num_actions):
            self.brain = Reinforce().Brain(num_states, num_actions)

        def update_Q_function(self, gamestate, action, reward, new_state):
            self.brain.update_Q_table(gamestate, action, reward, new_state)

        def get_action(self,gamestate, step):
            action = self.brain.decide_action(gamestate, step)
            return actions
    class Brain:
        def __init__(self, num_states, num_actions):
            self.num_actions =num_actions
            NUM_DIZITIZED = 6
            self.q_table = np.random.uniform(low=0, high=1, size=(NUM_DIZITIZED**num_states, num_actions))

        def bins(self,gamestate): #状態を数値に変
            poke_onoff=[0,0,0,0,0,0]
            for i in range(3):
                if i == gamestate.teams[0].primary:
                    poke_onoff[i] = 1
                if i == gamestate.teams[1].primary:
                    poke_onoff[i+3] = 1

            poke_hp=[0,0,0,0,0,0]
            for i in range(3):
                if gamestate.teams[0].poke_list[i].health/gamestate.teams[0].poke_list[i].final_stats['hp'] == 0:
                    poke_hp[i] = 0
                if gamestate.teams[1].poke_list[i].health/gamestate.teams[1].poke_list[i].final_stats['hp'] == 0:
                    poke_hp[i+3] = 0
                if 0 < gamestate.teams[0].poke_list[i].health/gamestate.teams[0].poke_list[i].final_stats['hp'] <=50:
                    poke_hp[i] = 1
                if 0 < gamestate.teams[1].poke_list[i].health/gamestate.teams[1].poke_list[i].final_stats['hp'] <=50:
                    poke_hp[i+3] = 1
                if 50 < gamestate.teams[0].poke_list[i].health/gamestate.teams[0].poke_list[i].final_stats['hp'] <= 100:
                    poke_hp[i] = 2
                if 50 < gamestate.teams[1].poke_list[i].health/gamestate.teams[1].poke_list[i].final_stats['hp'] <= 100:
                    poke_hp[i+3] = 2

            return poke_hp[0],poke_onoff[0],poke_hp[1],poke_onoff[1],poke_hp[2],poke_onoff[2],poke_hp[3],poke_onoff[3],poke_hp[4],poke_onoff[4],poke_hp[5],poke_onoff[5]
        def digitize_state(self,gamestate):
            poke1_hp, poke1_onoff, poke2_hp, poke2_onoff,poke3_hp,poke3_onoff,poke4_hp,poke4_onoff,poke5_hp,poke5_onoff,poke6_hp,poke6_onoff = Reinforce().Brain().bins(gamestate)
            state_number = (poke1_hp*poke1_onoff*6**5 + poke2_hp*poke2_onoff*6**4 + poke3_hp*poke3_onoff*6**3 +
            poke4_hp*poke4_onoff*6**2 + poke5_hp*poke5_onoff*6 + poke6_hp*poke6_onoff)
            return state_number

        def update_Q_table(self, gamestate, action, reward, new_state):
            state = self.digitize_state(gamestate)
            state_next = self.digitize_state(new_state)
            Max_Q_next = max(self.q_table[state_next][:])
            self.q_table[state, action] = self.q_table[state, action] + \
                ETA * (reward + GAMMA * Max_Q_next - self.q_table[state, action])

        def decide_action(self, gamestate, episode):
            state = self.digitize_state(gamestate)
            epsilon = 0.5 * (1 / (episode + 1))

            if epsilon <= np.random.uniform(0,1):
                action = np.argmax(self.q_table[state][:])
            else:
                action = np.random.choice(self.num_actions)
            return action

    class Environment:
        def __init__(self):
            num_state = 6
            num_actions = 6
            self.agent = Reinforce().Agent(num_state,num_actions)

        def get_random_action(self): ######youkenntou
            rate = np.random.randint(13)
            if rate < 10:
                random_action = move(np.random.randint(4),False)
            else:
                random_action = switch(np.random.randint(2))
            return random_action
        def run(self):
            complete_episodes = 0
            is_episode_final = False
            NUM_DIZITIZED = 6
            MAX_STEPS = 20
            NUM_EPISODES = 100
            from data import load_data
            poke_data = load_data("data")
            from gamestate import GameState
            from team import Team
            from smogon import Smogon
            import json
            #パーティー読み込み
            with open("teams/pokemon_team11.txt") as f1, open("teams/pokemon_team12.txt") as f2, open("data/poke2.json") as f3:
                data = json.loads(f3.read())
                poke_dict = Smogon.convert_to_dict(data)
                teams = [Team.make_team(f1.read(), poke_dict), Team.make_team(f2.read(), poke_dict)]
            gamestate = GameState(teams)
            simulator = Simulator(poke_data)
            for episode in range(NUM_EPISODES):
                for step in range(MAX_STEPS):
                    my_action = self.agent.get_action(gamestate,episode)
                    opp_action = get_random_action()
                    new_state = self.simulator.simulate(gamestate, [my_action,opp_action], who)
                    #報酬
                    if new_state.is_over():
                        reward = 0
                    else:
                        reward = 1
                        complete_episodes += 1
                    self.agent.update_Q_function(gamestate,my_action,reward,new_state)
                    gamestate = new_state
                    if is_episode_final is True:
                        break
                    if complete_episodes >= 10:
                        print('10回連続成功')
                        is_episode_final = True

env = Reinforce().Environment()
env.run()
'''
