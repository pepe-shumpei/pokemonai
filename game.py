#from smogon import Smogon
from team import Team
from gamestate import GameState
from simulator import Simulator
from agent import HumanAgent, PessimisticMinimaxAgent, OptimisticMinimaxAgent
from simulator import Action
from data import load_data
import time
#from reinforce import Agent
from evaluate import Evaluate
import numpy as np

def main():

    poke_data = load_data("data")
    players = [None, None]
    w = np.random.normal(0,0.5,150)
    #w = np.zeros(150)
    #w = np.load("weight.npy")
    evaluate = Evaluate(w)
    players[0] = PessimisticMinimaxAgent(1, poke_data, evaluate)
    players[1] = PessimisticMinimaxAgent(1, poke_data, evaluate)
    #players[1] = Agent(6,6)
    #qtable = np.load("qtable.npy")
    #players[1].brain.q_table = qtable

    from smogon import Smogon
    import json
    #パーティー読み込み
    with open("teams/pokemon_team2.txt") as f1, open("teams/pokemon_team2.txt") as f2, open("data/poke2.json") as f3:
        data = json.loads(f3.read())
        poke_dict = Smogon.convert_to_dict(data)
        teams = [Team.make_team(f1.read(), poke_dict), Team.make_team(f2.read(), poke_dict)]

    gamestate0 = GameState(teams)
    simulator = Simulator(poke_data)

    #edit
    #gamestate0.teams[0].poke_list[1].alive=False
    #gamestate0.teams[0].poke_list[2].alive=False
    #gamestate0.teams[1].poke_list[1].alive=False
    #gamestate0.teams[1].poke_list[2].alive=False
    count = 0
    win = 0
    lose = 0
    for i in range(10000):
        gamestate = gamestate0.deep_copy()
        while not gamestate.is_over():
            """
            print("==========================================================================================")
            print("my_team:",gamestate.teams[0].poke_list)
            print("opp_team:",gamestate.teams[1].poke_list)
            print("Player 1 primary:", gamestate.get_team(0).primary())
            print("Player 2 primary:", gamestate.get_team(1).primary())
            """

            #行動選択
            my_action = players[0].get_action(gamestate, 0, log=False)
            opp_action = players[1].get_action(gamestate, 1, log=False)
            #opp_action, _ = players[1].get_action(gamestate, 1000000000000,1) #Q-Learningのとき
            #opp_action = players[1].get_random_action(gamestate, 1)

            #行動前の評価値
            v1 = evaluate.evaluate(0, gamestate, child=True)

            #行動
            gamestate = simulator.simulate(gamestate, [my_action, opp_action], 0, log=False)

            #死んだときの交代
            my_dead_switch = players[0].get_dead_switch(gamestate, 0)
            if my_dead_switch != None: # Noneになるときは死んでない時or gameoverのとき
                gamestate.switch_pokemon(my_dead_switch, 0)
            opp_dead_switch = players[1].get_dead_switch(gamestate, 1)
            if opp_dead_switch != None:
                gamestate.switch_pokemon(opp_dead_switch, 1)

            #行動後の評価値
            v2 = evaluate.evaluate(0,gamestate, child=False)
            #雑巾絞り
            evaluate.zoukin(v1,v2)

            """
            p1 = evaluate.convert_winning_rate(v1)
            p2 = evaluate.convert_winning_rate(v2)
            print("p1...", p1)
            print("p2...", p2)
            print()
            """

        count += 1
        if gamestate.get_team(0).alive():
            win += 1
        else:
            lose += 1
        evaluate.eta = evaluate.eta * 0.9997
        if count % 100 == 0:

            print("win",win,"lose",lose,"count",count)
            print(evaluate.eta)
            win = 0
            lose = 0
    np.save("weight.npy", evaluate.w)


if __name__ == "__main__":
    main()
