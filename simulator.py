from move_list import moves as MOVES
from mega_items import mega_items as MEGA_ITEMS
#from log import SimulatorLog #とりあえず使わない
#from data import MOVE_CORRECTIONS, get_hidden_power, correct_mega, get_move
import random
class Simulator():

    def __init__(self, pokedata):
        #self.log = SimulatorLog() #とりあえず使わない
        self.smogon_data = pokedata.smogon_data
        self.pokedata = pokedata
        for move_name, move in MOVES.items(): #?
            move.pokedata = pokedata
        self.score = 0
        self.total = 0
        self.latest_turn = None


    #素早さ計算
    def get_first(self, gamestate, moves, who=0, log=False):
        my_move = moves[who]
        opp_move = moves[1 - who]

        my_team = gamestate.get_team(who)
        opp_team = gamestate.get_team(1 - who)

        my_poke = my_team.primary()
        opp_poke = opp_team.primary()

        #ランク変化
        my_speed = my_poke.get_stage('spe')
        opp_speed = opp_poke.get_stage('spe')

        my_spe_buffs = 1.0 + 0.5 * abs(my_speed)
        opp_spe_buffs = 1.0 + 0.5 * abs(opp_speed)

        my_spe_multiplier = my_spe_buffs if my_speed > 0 else 1 / my_spe_buffs
        opp_spe_multiplier = opp_spe_buffs if opp_speed > 0 else 1 / opp_spe_buffs
        #こだわりスカーフ
        if my_poke.item == "Choice Scarf":
            my_spe_multiplier *= 1.5
        if opp_poke.item == "Choice Scarf":
            opp_spe_multiplier *= 1.5
        #麻痺
        my_paralyze = 0.5 if my_poke.status == "paralyze" else 1.0
        opp_paralyze = 0.5 if opp_poke.status == "paralyze" else 1.0
        #素早さ計算（最終）
        my_final_speed = my_poke.get_stat("spe") * my_spe_multiplier * my_paralyze
        opp_final_speed = opp_poke.get_stat("spe") * opp_spe_multiplier * opp_paralyze
        #優先度プラス
        #はやてのつばさ
        if my_poke.ability == "Gale Wings":
            if my_move.type == "Flying":
                my_move.priority += 1
        if opp_poke.ability == "Gale Wings":
            if opp_move.type == "Flying":
                opp_move.priority += 1
        #いたずらごころ
        if my_poke.ability == "Prankster":
            if my_move.category != "Physical" and my_move.category != "Special":
                my_move.priority += 1
        if opp_poke.ability == "Prankster":
            if opp_move.category != "Physical" and opp_move.category != "Special":
                opp_move.priority += 1

        first = None
        if my_move.priority > opp_move.priority:
            first = who
        elif opp_move.priority > my_move.priority:
            first = 1 - who
        else:
            if my_final_speed > opp_final_speed:
                first = who
            elif opp_final_speed > my_final_speed:
                first = 1 - who
            else:
                first = random.randint(0,1)
        return first
    #シミュレーション
    def simulate(self, gamestate, actions, who, log=False):
        assert not gamestate.is_over()
        #TeamをそれぞれReturn
        my_team = gamestate.get_team(who)
        opp_team = gamestate.get_team(1 - who)
        #盤面のポケモンをReturn
        my_poke = my_team.primary()
        opp_poke = opp_team.primary()
        #GameStateをdeepcopy
        gamestate = gamestate.deep_copy()
        #それぞれの行動
        my_action = actions[who]
        opp_action = actions[1 - who]
        #交代したとき（交代の順番が固定はおかしい！）
        if my_action.is_switch():
            gamestate.switch_pokemon(my_action.switch_index, who, log=log)
            my_move = MOVES["Noop"]
            my_poke = my_team.primary()
        if opp_action.is_switch():
            gamestate.switch_pokemon(opp_action.switch_index, 1 - who, log=log)
            opp_move = MOVES["Noop"]
            opp_poke = opp_team.primary()
        #攻撃したとき(get_moveが完全に間違っている)
        if my_action.is_move():
            my_move = my_poke.moveset.moves[my_action.move_index]
        if opp_action.is_move():
            opp_move = opp_poke.moveset.moves[opp_action.move_index]

        moves = [None, None]
        moves[who] = my_move
        moves[1 - who] = opp_move
        #素早さ判定
        first = self.get_first(gamestate, moves, who)

        self.make_move(gamestate, moves, actions, first, who, log=log)
        return gamestate

    def make_move(self, gamestate, moves, actions, first, who, log=False,):
        #メガ進化
        for i in [first, 1 - first]:
            team = gamestate.get_team(i)
            action = actions[i]
            if action.mega:
                team.poke_list[team.primary_poke] = team.primary().mega_evolve(self.pokedata, log=log)
                gamestate.switch_pokemon(team.primary_poke, i, log=log, hazards=False)

        #技使用
        for i in [first, 1 - first]:
            team = gamestate.get_team(i)
            other_team = gamestate.get_team(1 - i)

            move = moves[i]
            action = actions[i]
            other_action = actions[1 - i]
            #技発動
            damage = move.handle(gamestate, i, log=log)
            if log:
                print ("%s used %s and dealt %u damage." % (
                    team.primary(),
                    move.name,
                    damage
                ))
            #ふうせん
            if damage > 0 and other_team.primary().item == "Air Balloon":
                other_team.primary().item = None
            #とんぼがえり、ボルトチェンジ
            if damage > 0 and move.name in ["U-turn", "Volt Switch"] and action.volt_turn is not None:
                gamestate.switch_pokemon(action.volt_turn, i, log=log)

            if other_team.primary().health == 0:
                other_team.primary().alive = False
                if log:
                    print (
                        "%s fainted." % other_team.primary()
                    )

            if gamestate.is_over():
                return

            if not other_team.primary().alive:
                    #gamestate.switch_pokemon(other_action.backup_switch, 1 - i, log=log)
                break

class Action(): #死ぬ前に交代先を決める仕組み？
    def __init__(self, type, move_index=None, switch_index=None, backup_switch=None,mega=False, volt_turn=None):
        self.type = type
        self.move_index = move_index
        self.switch_index = switch_index
        self.backup_switch = backup_switch
        self.mega = mega
        self.volt_turn = volt_turn

    def is_move(self):
        return self.type == "move"
    def is_switch(self):
        return self.type == "switch"

    def __eq__(self, other):
        if self.type != other.type:
            return False
        if self.type == "move":
            return (self.move_index == other.move_index and self.mega == other.mega and self.volt_turn == other.volt_turn)
        if self.type == "switch":
            return (self.switch_index == other.switch_index)
        return False

    def __hash__(self):
        if self.type == "move":
            return hash(self.type, self.move_index, self.mega)
        if self.type == "switch":
            return (self.type, self.switch_index)
    #あとでなおす
    @staticmethod
    def create(move_string):
        splt = move_string.strip().split()
        if len(splt) == 4:
            volt_turn = None
            type, index, backup, str_mega = splt
        if len(splt) == 5:
            type, index, backup, str_mega, volt_turn = splt
        index = int(index)
        backup = None if backup == "None" else int(backup)
        mega = True if str_mega == "True" else False
        volt_turn = int(volt_turn) if volt_turn is not None else None
        return Action(type, move_index=index, switch_index=index, mega=mega, backup_switch=backup, volt_turn=volt_turn)

    def __repr__(self):
        if self.type == "move":
            if self.volt_turn is None:
                return "%s(%u, %s)" % (self.type, self.move_index, self.mega)
            else:
                return "%s(%u, %s, %u)" % (self.type, self.move_index, self.mega, self.volt_turn)
        elif self.type == "switch":
            return "%s(%s)" % (self.type, self.switch_index)
