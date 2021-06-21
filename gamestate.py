import pickle
from simulator import Action
from type import get_multiplier
import numpy as np
#from data import MOVES
import logging
logging.basicConfig()

class GameState():
    def __init__(self, teams):
        self.teams = teams #[Team, Team] ←class Team
        self.rocks = [False, False] #rocks=ステルスロック
        self.spikes = [0, 0] #spiles=まきびし
        
    #copy Gamestate
    def deep_copy(self):
        state = GameState([x.copy() for x in self.teams])
        state.rocks = self.rocks[:]
        state.spikes = self.spikes[:]
        return state
    #ステルスロック
    def set_rocks(self, who, rock_bool):
        self.rocks[who] = rock_bool
    #まきびし
    def add_spikes(self, who):
        self.spikes[who] += 1
    #チームの呼び出し
    def get_team(self, team):
        return self.teams[team]
    #タプルでポケモンとステロ、まきびしをReturn
    def to_tuple(self):
        return (tuple(x.to_tuple() for x in self.teams), (self.rocks[0], self.rocks[1], self.spikes[0], self.spikes[1]))

    @staticmethod
    def from_tuple(tupl):
        return GameState([team.from_tuple() for team in tupl[0]])
    #評価関数
    def evaluate2(self, who):
        win_bonus = 0
        my_team = self.get_team(who)
        opp_team = self.get_team(1 - who)
        if self.is_over():
            if my_team.alive():
                win_bonus = 10000
            else:
                win_bonus = -10000
        #teamのHPの合計
        my_team_health = sum([x.health/x.final_stats['hp'] for x in my_team.poke_list])
        opp_team_health = sum([x.health/x.final_stats['hp'] for x in opp_team.poke_list])
        #ポケモンの死亡数
        my_team_death = len([x for x in my_team.poke_list if not x.alive])
        opp_team_death = len([x for x in opp_team.poke_list if not x.alive])

        my_burn, opp_burn = 0, 0 #やけど
        my_rocks, opp_rocks = 0, 0 #ステルスロック
        spikes = 0 #まきびし
        if self.is_over():
            my_team_stages, opp_team_stages = 0, 0
        else:
            #盤面ポケ
            my_poke = my_team.primary()
            opp_poke = opp_team.primary()
            #teamのランク変化の合計
            my_team_stages = my_poke.stages['spatk'] + my_poke.stages['patk']
            opp_team_stages = opp_poke.stages['spatk'] + opp_poke.stages['patk']
            #ステルスロック評価
            opp_rocks = 0.75 if self.rocks[1 - who] else 0
            my_rocks = -1.0 if self.rocks[who] else 0
            #まきびし評価
            if self.spikes[1 - who] == 1:
                spikes = 0.3
            elif self.spikes[1 - who] == 2:
                spikes = 0.6
            elif self.spikes[1 - who] == 3:
                spikes = 1
            #やけど評価
            opp_burn = 0.75 if (opp_poke.status == "burn" and opp_poke.final_stats['patk'] > 245 and opp_poke.ability != "Guts") else 0
            my_burn = -1.5 if (my_poke.status == "burn" and my_poke.final_stats['patk'] > 250 and my_poke.ability != "Guts") else 0
        return win_bonus + my_team_health - opp_team_health - 0.5 * my_team_death + 0.5 * opp_team_death + opp_rocks + my_rocks + opp_burn + my_burn + spikes# + 0.07 * (my_team_stages - opp_team_stages)


    def is_over(self):
        return not (self.teams[0].alive() and self.teams[1].alive())


    #交代
    def switch_pokemon(self, switch_index, who, log=False, hazards=True):
        my_team = self.get_team(who)
        opp_team = self.get_team(1 - who)
        my_team.set_primary(switch_index) #交代
        my_poke = my_team.primary() #盤面ポケセット
        my_poke.reset_taunt() #ちょうはリセット
        my_poke.reset_disabled() #かなしばりリセット
        my_poke.reset_last_move()
        my_poke.reset_encore()
        opp_poke = opp_team.primary()
        if log:
            print("%s switched in." %my_poke)

        #いかく
        if my_poke.ability == "Intimidate":
            if log:
                print ("%s got intimidated." % opp_poke)
            opp_poke.decrease_stage('patk', 1)

        #ステルスロック
        if self.rocks[who] and hazards:
            type = 1.0
            type_multipliers = [get_multiplier(x, "Rock") for x in my_poke.typing]
            for x in type_multipliers:
                type *= x
            damage = 1.0 / 8 * type
            d = my_poke.damage_percent(damage)
            if log:
                print ("%s was damaged %f due to rocks!" % (my_poke, d))
        #まきびし　
        if self.spikes[who] > 0 and "Flying" not in my_poke.typing and my_poke.ability != "Levitate":
                if self.spikes[who] == 1:
                    d = my_poke.damage_percent(1.0 / 8)
                elif self.spikes[who] == 2:
                    d = my_poke.damage_percent(1.0 / 6)
                elif self.spikes[who] == 3:
                    d = my_poke.damage_percent(1.0 / 4)
                if log:
                    print("%s was damaged %f due to spikes!" % (my_poke, d))


    #できる行動の取得
    def get_legal_actions(self, who, log=False):
        my_team = self.get_team(who)
        my_poke = my_team.primary()
        opp_team= self.get_team(1 - who)
        opp_poke = opp_team.primary()

        pokemon = range(len(my_team.poke_list)) #list = [0,1,2,3,4,5,6]
        valid_switches = [i for i in pokemon if my_team.poke_list[i].alive and i != my_team.primary_poke]
        #print("valid_switches",who,valid_switches)
        valid_backup_switches = valid_switches + [my_team.primary_poke]
        if len(valid_switches) == 0:
            valid_switches = [None]

        moves = []
        switches = []
        for move_index in range(len(my_poke.moveset.moves)):
            move_name = my_poke.moveset.moves[move_index]
            mega = my_poke.can_evolve()
            #こだわりロック
            if my_poke.choiced:
                if move_name.name != my_poke.move_choice:
                    continue

            #とんぼ返りorボルトチェンジのとき(backup_switchあとでなくす)
            if move_name == "U-turn" or move_name == "Volt Switch":
                for j in valid_switches:
                    for k in valid_backup_switches:
                        if j == None:
                            moves.append(
                                Action(
                                    "move",
                                    move_index=move_index,
                                    mega=mega,
                                    volt_turn=j,
                                    backup_switch=None
                                )
                            )
                        elif j != None and k != None and j != k:
                            moves.append(
                                Action(
                                    "move",
                                    move_index=move_index,
                                    volt_turn=j,
                                    backup_switch=k,
                                    mega=mega
                                )
                            )
            else:
                moves.append(Action("move", move_index=move_index, mega=mega))
        switches.extend([Action("switch", switch_index=i) for i in valid_switches if i is not None])
        #print("moves",moves,"switches",switches)
        #磁力
        if opp_poke.ability == "Magnet Pull" and "Steel" in my_poke.typing and "Ghost" not in my_poke.typing:
            switches = []
        #かげふみ
        elif opp_poke.ability == "Shadow Tag" and "Ghost" not in my_poke.typing:
            switches = []
        #ありじごく
        elif opp_poke.ability == "Arena Trap" and "Ghost" not in my_poke.typing and "Flying" not in my_poke.typing:
            switches = []

        #ちょうはつ
        if my_poke.taunt:
            moves = [move for move in moves if MOVES[my_poke.moves[move.move_index]].category != "Non-Damaging"]
        #かなしばり
        if my_poke.disabled is not None:
            moves = [move for move in moves if my_poke.moves[move.move_index] != my_poke.disabled]

        #アンコール
        if my_poke.encore:
            moves = [move for move in moves if my_poke.moves[move.move_index] == my_poke.last_move]



        return moves + switches
