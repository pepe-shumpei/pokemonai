from simulator import Simulator, Action

import logging
import time

import numpy as np
logging.basicConfig()
GAMMA = 1.0
ETA = 0.5
MAX_STEPS = 20
NUM_EPISODES = 1000
num_state = 6
num_actions = 6
NUM_DIZITIZED = 6
from data import load_data
poke_data = load_data("data")
from gamestate import GameState
from team import Team
from smogon import Smogon
from agent import HumanAgent, PessimisticMinimaxAgent, OptimisticMinimaxAgent
import json
#パーティー読み込み
with open("teams/pokemon_team6.txt") as f1, open("teams/pokemon_team6.txt") as f2, open("data/poke2.json") as f3:
    data = json.loads(f3.read())
    poke_dict = Smogon.convert_to_dict(data)
    teams = [Team.make_team(f1.read(), poke_dict), Team.make_team(f2.read(), poke_dict)]
gamestate = GameState(teams)
simulator = Simulator(poke_data)
opp_player = PessimisticMinimaxAgent(1, poke_data)



class Agent:
    def __init__(self, num_states, num_actions):
        self.brain = Brain(num_states, num_actions)

    def update_Q_function(self,state, action, reward, new_state):
        self.brain.update_Q_table(state, action, reward, new_state)
    def update_nstep_function(self,state, action, reward, new_state):
        self.brain.update_n_step_table(state, action, reward, new_state)
    def get_action(self,state, step, who,EXCHANGE):
        action = self.brain.decide_action(state, step, who,EXCHANGE)
        return action

    def get_Q_table(self,state):
        state = self.brain.digitize_state(state)
        table = self.brain.q_table[state][:]
        print("state",state)
        print(table)

    def get_dead_switch(self, state, who):
        my_team = state.teams[who]
        if my_team.primary().alive:
            return None
        pokemon = range(len(my_team.poke_list))
        valid_switches = [i for i in pokemon if my_team.poke_list[i].alive and i != my_team.primary_poke]
        if valid_switches == []:
            return None
        choice = np.random.choice(valid_switches)
        return choice

class Brain:
    def __init__(self, num_states, num_actions):
        self.num_actions =num_actions
        NUM_DIZITIZED = 6
        self.q_table = np.random.uniform(low=1, high=1, size=(NUM_DIZITIZED**num_states, num_actions))

    def bins(self,state): #状態を数値に変換
        poke_onoff=[0,0,0,0,0,0]
        for i in range(3):
            if i == state.teams[0].primary_poke:
                poke_onoff[i] = 1
            if i == state.teams[1].primary_poke:
                poke_onoff[i+3] = 1

        poke_hp=[0,0,0,0,0,0]
        for i in range(3):
            if state.teams[0].poke_list[i].health/state.teams[0].poke_list[i].final_stats['hp'] == 0:
                poke_hp[i] = 0
            if state.teams[1].poke_list[i].health/state.teams[1].poke_list[i].final_stats['hp'] == 0:
                poke_hp[i+3] = 0
            if 0 < state.teams[0].poke_list[i].health/state.teams[0].poke_list[i].final_stats['hp'] <=50:
                poke_hp[i] = 1
            if 0 < state.teams[1].poke_list[i].health/state.teams[1].poke_list[i].final_stats['hp'] <=50:
                poke_hp[i+3] = 1
            if 50 < state.teams[0].poke_list[i].health/state.teams[0].poke_list[i].final_stats['hp'] <= 100:
                poke_hp[i] = 2
            if 50 < state.teams[1].poke_list[i].health/state.teams[1].poke_list[i].final_stats['hp'] <= 100:
                poke_hp[i+3] = 2

        return poke_hp[0],poke_onoff[0],poke_hp[1],poke_onoff[1],poke_hp[2],poke_onoff[2],poke_hp[3],poke_onoff[3],poke_hp[4],poke_onoff[4],poke_hp[5],poke_onoff[5]
    def digitize_state(self,state):
        list = [[0,1,2],[3,4,5]]
        poke1_hp, poke1_onoff, poke2_hp, poke2_onoff,poke3_hp,poke3_onoff,poke4_hp,poke4_onoff,poke5_hp,poke5_onoff,poke6_hp,poke6_onoff = self.bins(state)
        #print(poke1_hp, poke1_onoff, poke2_hp, poke2_onoff,poke3_hp,poke3_onoff,poke4_hp,poke4_onoff,poke5_hp,poke5_onoff,poke6_hp,poke6_onoff)
        state_number = list[poke1_onoff][poke1_hp]*6**5 +  list[poke2_onoff][poke2_hp]*6**4 + list[poke3_onoff][poke3_hp]*6**3 + list[poke4_onoff][poke4_hp]*6**2 \
         + list[poke5_onoff][poke5_hp]*6**1 + list[poke6_onoff][poke6_hp]*6**0
        #state_number = poke1_hp*poke1_onoff*6**5 + poke2_hp*poke2_onoff*6**4 + poke3_hp*poke3_onoff*6**3 +poke4_hp*poke4_onoff*6**2 + poke5_hp*poke5_onoff*6 + poke6_hp*poke6_onoff
        #print("state_number:",state_number)
        return state_number

    def update_Q_table(self, state, action, reward, new_state):
        state = self.digitize_state(state)
        state_next = self.digitize_state(new_state)
        Max_Q_next = max(self.q_table[state_next][:])
        #print("state:", state, self.q_table[state][:])
        #print("state_next:", state_next, self.q_table[state_next][:])
        self.q_table[state,action] = self.q_table[state,action] + \
            ETA * (reward + GAMMA * Max_Q_next - self.q_table[state,action])
        #print("update_state:", state, self.q_table[state][:])


    def update_n_step_table(self, state0, action, n_reward, new_state):
        state = self.digitize_state(state0)
        state_next = self.digitize_state(new_state)
        Max_Q_next = max(self.q_table[state_next][:])
        reward=0
        for a in range(len(n_reward)):
            reward += n_reward[a] * GAMMA**a
        self.q_table[state,action] = self.q_table[state,action] + \
            ETA * (reward + GAMMA**len(n_reward) * Max_Q_next - self.q_table[state,action])
    def get_random_action(self,state,who): ######youkenntou
        rate = np.random.randint(9)
        if rate < 10:
            action_number=np.random.randint(4)
            random_action = Action('move',action_number,False)
        else:
            '''
            my_team = state.teams[who]
            pokemon = range(len(my_team.poke_list))
            valid_switches = [i for i in pokemon if my_team.poke_list[i].alive and i != my_team.primary_poke]
            action_number = np.random.choice(valid_switches)
            '''
            random_action = Action('switch',action_number)
        return random_action,action_number
    def decide_switch(self,state,state_number,action_n,who):
        switch_n = None
        if action_n == 4:
            if state.teams[who].primary_poke == 0:
                if state.teams[who].poke_list[1].alive:
                    switch_n = 1
                else:
                    self.q_table[state_number,4] = -100
            if state.teams[who].primary_poke == 1:
                if state.teams[who].poke_list[0].alive:
                    switch_n = 0
                else:
                    self.q_table[state_number,4] = -100
            if state.teams[who].primary_poke == 2:
                if state.teams[who].poke_list[0].alive:
                    switch_n = 0
                else:
                    self.q_table[state_number,4] = -100
        if action_n == 5:
            if state.teams[who].primary_poke == 0:
                if state.teams[who].poke_list[2].alive:
                    switch_n = 2
                else:
                    self.q_table[state_number,5] = -100
            if state.teams[who].primary_poke == 1:
                if state.teams[who].poke_list[2].alive:
                    switch_n = 2
                else:
                    self.q_table[state_number,5] = -100
            if state.teams[who].primary_poke == 2:
                if state.teams[who].poke_list[1].alive:
                    switch_n = 1
                else:
                    self.q_table[state_number,5] = -100
        return switch_n
    def decide_action(self, state, episode,who,EXCHANGE):
        state_number = self.digitize_state(state)
        epsilon = 0.5 * (1000/ (episode + 1000))

        if epsilon <= np.random.uniform(0,1):########################################
            action_n = np.argmax(self.q_table[state_number][:])

            if action_n == 4:
                EXCHANGE += 1
            if action_n == 5:
                EXCHANGE += 1

            switch_n = self.decide_switch(state,state_number,action_n,who)
            action_n = np.argmax(self.q_table[state_number][:])
            switch_n = self.decide_switch(state,state_number,action_n,who)
            action_n = np.argmax(self.q_table[state_number][:])
            #if state.teams[who].poke_list[2].alive:
                #print(state.teams[who].poke_list[2].alive)

            if action_n <= 3:
                action = Action('move', action_n,False)
                action_number = action_n
            else:
                EXCHANGE += 1
                action = Action('switch', switch_index=switch_n)
                action_number = action_n
        else:
            action,action_number = self.get_random_action(state,who)
        return action,action_number

class Environment:
    def __init__(self):
        num_state = 6
        num_actions = 6
        self.agent1 = Agent(num_state,num_actions)
        self.agent2 = Agent(num_state,num_actions)

    def get_random_action(self,state,who): ######youkenntou
        rate = np.random.randint(9)
        if rate < 10: #なおす！！！このままでは交代できない
            action_number=np.random.randint(4)
            random_action = Action('move',action_number,False)
        else:
            my_team = state.teams[who]
            pokemon = range(len(my_team.poke_list))
            valid_switches = [i for i in pokemon if my_team.poke_list[i].alive and i != my_team.primary_poke]
            action_number = np.random.choice(valid_switches)
            random_action = Action('switch',action_number)
        return random_action,action_number

    def run(self,gamestate):
        complete_episodes = 0
        is_episode_final = False
        NUM_DIZITIZED = 6
        MAX_STEPS = 30
        NUM_EPISODES = 200000
        win = 0
        lose = 0
        EXCHANGE = 0
        for episode in range(NUM_EPISODES):
            for step in range(MAX_STEPS):
                if step == 0:
                    state = gamestate.deep_copy()
                    """
                    if episode > -1:
                        self.agent.get_Q_table(state)
                    """

                if episode > -1:
                    """
                    print("==========================================================================================")
                    print("step",step)
                    print("my_team:",state.teams[0].poke_list)
                    print("opp_team:",state.teams[1].poke_list)
                    print("Player 1 primary:", state.get_team(0).primary())
                    print("Player 2 primary:", state.get_team(1).primary())
                    print("opp_team:",state.teams[1].poke_list[0].alive,state.teams[1].poke_list[1].alive,state.teams[1].poke_list[2].alive)
                    """

                my_action,my_action_number = self.agent1.get_action(state,episode,0,EXCHANGE)
                #my_action,my_action_number = self.get_random_action(state,0)
                opp_action,opp_action_number = self.get_random_action(state,0)
                #opp_action = opp_player.get_action(state, 1,log=False)
                #opp_action,opp_action_number = self.agent2.get_action(state,episode,1)


                if episode > 10000:
                    log = True
                else:
                    log = False

                new_state = simulator.simulate(state, [my_action,opp_action],0, log=False)

                #死んだときの交代
                my_dead_switch = self.agent1.get_dead_switch(new_state, 0)
                #print(my_dead_switch)
                if my_dead_switch != None: # Noneになるときは死んでない時or gameoverのとき
                    #print("瀕死交代")
                    new_state.switch_pokemon(my_dead_switch, 0)
                opp_dead_switch = self.agent2.get_dead_switch(new_state, 1)
                #print(opp_dead_switch)
                if opp_dead_switch != None:
                    #print("瀕死交代")
                    new_state.switch_pokemon(opp_dead_switch, 1)

                #報酬
                if not new_state.is_over():
                    reward =0
                else:
                    if new_state.get_team(0).alive():
                        reward = 1
                        win += 1
                    else:
                        reward = -1
                        lose += 1


                self.agent1.update_Q_function(state,my_action_number,reward,new_state)
                #self.agent2.update_Q_function(state,opp_action_number,reward*(-1),new_state)
                state = new_state
                if new_state.is_over():
                    """
                    if gamestate.get_team(0).alive():
                        print("You win!")
                    else:
                        print("You lose!")
                    """
                    complete_episodes += 1
                    break
            if is_episode_final is True:
                break
            """
            if complete_episodes >= 20:
                print('20回連続成功')
                is_episode_final = False
            """
            if complete_episodes == 1000:
                print("win:",win,"lose:",lose,"episode",episode,"EXCHANGE",EXCHANGE)
                complete_episodes = 0
                win = 0
                lose = 0

    def run_nstep(self,gamestate):
        complete_episodes = 0
        is_episode_final = False
        NUM_DIZITIZED = 6
        MAX_STEPS = 20
        NUM_EPISODES = 1000
        win = 0
        lose = 0
        nstep = 10
        n_reward=[]
        for episode in range(NUM_EPISODES):
            gamestate0 = gamestate.deep_copy()

            for step in range(MAX_STEPS):
                """
                print("==========================================================================================")
                print('step',step)
                print("my_team:",gamestate.teams[0].poke_list)
                print("opp_team:",gamestate.teams[1].poke_list)
                print("Player 1 primary:", gamestate.get_team(0).primary())
                print("Player 2 primary:", gamestate.get_team(1).primary())
                """
                state = gamestate.deep_copy()
                state0 = gamestate.deep_copy()
                for n in range(nstep):
                    my_action,my_action_number = self.agent.get_action(state,episode,0)
                    opp_action,opp_action_number = self.get_random_action(state,1)
                    new_state = simulator.simulate(state, [my_action,opp_action],0, log=False)

                    #死んだときの交代
                    my_dead_switch = self.agent.get_dead_switch(new_state, 0)
                    #print(my_dead_switch)
                    if my_dead_switch != None: # Noneになるときは死んでない時or gameoverのとき
                        #print("瀕死交代")
                        new_state.switch_pokemon(my_dead_switch, 0)
                    opp_dead_switch = self.agent.get_dead_switch(new_state, 1)
                    #print(opp_dead_switch)
                    if opp_dead_switch != None:
                        #print("瀕死交代")
                        new_state.switch_pokemon(opp_dead_switch, 1)

                    #報酬
                    if not new_state.is_over():
                        reward = 0.01
                    else:
                        if new_state.get_team(0).alive():
                            reward = 0.3


                        else:
                            reward = -0.3

                    n_reward.append(reward)
                    if new_state.is_over():
                        break
                state = new_state
                print("==========================================================================================")
                print('step',step)
                print("my_team:",gamestate.teams[0].poke_list)
                print("opp_team:",gamestate.teams[1].poke_list)
                print("Player 1 primary:", gamestate.get_team(0).primary())
                print("Player 2 primary:", gamestate.get_team(1).primary())

                self.agent.update_nstep_function(state0,my_action_number,n_reward,new_state)
                my_action,my_action_number = self.agent.get_action(state0,episode,0)
                opp_action,opp_action_number = self.get_random_action(state0,1)
                next_state = simulator.simulate(state0, [my_action,opp_action],0, log=False)

                #死んだときの交代
                my_dead_switch = self.agent.get_dead_switch(next_state, 0)
                #print(my_dead_switch)
                if my_dead_switch != None: # Noneになるときは死んでない時or gameoverのとき
                    #print("瀕死交代")
                    next_state.switch_pokemon(my_dead_switch, 0)
                opp_dead_switch = self.agent.get_dead_switch(next_state, 1)
                #print(opp_dead_switch)
                if opp_dead_switch != None:
                    #print("瀕死交代")
                    next_state.switch_pokemon(opp_dead_switch, 1)

                gamestate = next_state
                if not next_state.is_over():
                    pass
                else:
                    if next_state.get_team(0).alive():
                        win += 1
                    else:
                        lose += 1
                if next_state.is_over():
                    """
                    if gamestate.get_team(0).alive():
                        print("You win!")
                    else:
                        print("You lose!")
                    """
                    gamestate = gamestate0
                    complete_episodes += 1
                    break
            '''
            if is_episode_final is True:
                break

            if complete_episodes >= 20:
                print('20回連続成功')
                is_episode_final = False
            '''
            #print(complete_episodes)
            if complete_episodes == 100:
                print("win:",win,"lose:",lose)
                complete_episodes = 0
                win = 0
                lose = 0

    def run_test(self,gamestate):
        complete_episodes = 0
        is_episode_final = False
        NUM_DIZITIZED = 6
        MAX_STEPS = 20
        NUM_EPISODES = 10
        win = 0
        lose = 0
        for episode in range(NUM_EPISODES):
            episode = 1000000
            gamestate0 = gamestate.deep_copy()

            for step in range(MAX_STEPS):
                print("==========================================================================================")
                print("step",step)
                print("my_team:",gamestate.teams[0].poke_list)
                print("opp_team:",gamestate.teams[1].poke_list)
                print("Player 1 primary:", gamestate.get_team(0).primary())
                print("Player 2 primary:", gamestate.get_team(1).primary())
                state = gamestate.deep_copy()
                my_action,my_action_number = self.agent.get_action(state,episode,0)
                opp_action,opp_action_number = self.get_random_action(state,1)
                new_state = simulator.simulate(state, [my_action,opp_action],0, log=True)

                #死んだときの交代
                my_dead_switch = self.agent.get_dead_switch(new_state, 0)
                #print(my_dead_switch)
                if my_dead_switch != None: # Noneになるときは死んでない時or gameoverのとき
                    #print("瀕死交代")
                    new_state.switch_pokemon(my_dead_switch, 0)
                opp_dead_switch = self.agent.get_dead_switch(new_state, 1)
                #print(opp_dead_switch)
                if opp_dead_switch != None:
                    #print("瀕死交代")
                    new_state.switch_pokemon(opp_dead_switch, 1)

                #報酬
                if not new_state.is_over():
                    reward = 0
                else:
                    if new_state.get_team(0).alive():
                        reward = 10
                        win += 1
                    else:
                        reward = 0
                        lose += 1

                '''
                self.agent.update_Q_function(state,my_action_number,reward,new_state)
                '''


                if new_state.is_over():
                    """
                    if gamestate.get_team(0).alive():
                        print("You win!")
                    else:
                        print("You lose!")
                    """
                    gamestate = gamestate0
                    complete_episodes += 1
                    break
                gamestate = new_state
            if is_episode_final is True:
                break
            """
            if complete_episodes >= 20:
                print('20回連続成功')
                is_episode_final = False
            """
            if complete_episodes == 10:
                print("win:",win,"lose:",lose)
                complete_episodes = 0
                win = 0
                lose = 0




if __name__ == "__main__":
    env = Environment()
    env.run(gamestate)
    q = env.agent2.brain.q_table
    np.save("qtable.npy", q)
    #env.run_nstep(gamestate)
    #env.run_test(gamestate)
