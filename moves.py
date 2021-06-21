from type import get_multiplier

from handlers import void_handler


class Move:
    def __init__(self, name,
                 power=0,
                 category=None,
                 priority=0,
                 type=None,
                 accuracy=1.0,
                 handler=void_handler,
                 power_handler=None,
                 ):
        self.name = name
        self._power = power
        self.category = category
        self.type = type
        self.accuracy = accuracy
        self.handler = handler
        self.priority = priority
        self.power_handler = power_handler

    #__repr__ Objectが登場するところでReturn
    def __repr__(self):
        return self.name

    def power(self, gamestate, who):
        if self.power_handler is not None:
            return self.power_handler(gamestate, who)
        return self._power

    def handle(self, gamestate, who, log=False):
        return self.handler(gamestate, 0, who)


class BoostingMove(Move):
    def __init__(self, name,
                 boosts={},
                 category=None,
                 priority=0,
                 type=None,
                 accuracy=1.0,
                 handler=void_handler,
                 ):
        Move.__init__(self, name,
                      category=category,
                      priority=priority,
                      type=type,
                      accuracy=accuracy,
                      handler=handler
                      )
        self.boosts = boosts

    def handle(self, gamestate, who, log=False):
        poke = gamestate.get_team(who).primary()
        for boost, amount in self.boosts.items():
            if amount > 0:
                poke.increase_stage(boost, amount)
            else:
                poke.decrease_stage(boost, -amount)
        return 0

class DamagingMove(Move):

    def handle(self, gamestate, who, log=False):
        #攻撃側、防御側代入
        attacker = gamestate.get_team(who).primary()
        defender = gamestate.get_team(1 - who).primary()
        #物理 or 特殊
        if self.category == "Physical":
            atks = "patk"
            defs = "pdef"
        else:
            atks = "spatk"
            defs = "spdef"
        #サイコショック系
        if self.name == "Secret Sword" or self.name == "Psyshock":
            defs = "pdef"
        #攻撃力、防御力代入
        attack = attacker.get_stat(atks)
        defense = defender.get_stat(defs)
        #ランク変化
        abs_atk_buffs = 1.0 + 0.5 * abs(attacker.get_stage(atks))
        abs_def_buffs = 1.0 + 0.5 * abs(defender.get_stage(defs))
        atk_stage_multiplier = abs_atk_buffs if attacker.get_stage(atks) > 0 else 1 / abs_atk_buffs
        def_stage_multiplier = abs_def_buffs if defender.get_stage(defs) > 0 else 1 / abs_def_buffs
        type = 1
        #攻撃側タイプ
        move_type = self.type
        #技の名前
        name = self.name
        #技の威力
        power = self.power(gamestate, who)
        #ダメージ（攻撃力、防御力換算）
        other = 1.0 * atk_stage_multiplier / def_stage_multiplier
        #防御側の元の特性
        old_ability = defender.ability
        #特性効果
        if (attacker.ability == "Mold Breaker" or attacker.ability == "Turboblaze" or attacker.ability == "Teravolt") and defender.ability in self.pokedata.moldbreaker:
            defender.ability = None
        #フェアリースキン
        if attacker.ability == "Pixilate":
            if move_type == "Normal":
                move_type = "Fairy"
                other *= 1.3
        #スカイスキン
        if attacker.ability == "Aerilate":
            if move_type == "Normal":
                move_type = "Flying"
                other *= 1.3
        #へんげんじざい
        if attacker.ability == "Protean":
            attacker.typing = [move_type]
        #ふゆう
        if (defender.ability == "Levitate" or defender.item == "Air Balloon") and move_type == "Ground":
            other *= 0
        #テクニシャン
        if attacker.ability == "Technician" and power <= 60:
            other *= 1.5
        #あついしぼう
        if defender.ability == "Thick Fat" and (move_type == "Fire" or move_type == "Ice"):
            other *= 0.5

        #はたきおとす
        if self.name == "Knock Off" and defender.item is not None:
            other *= 1.5
        #こだわりロック
        if attacker.item in set(["Choice Scarf", "Choice Band", "Choice Specs"]):
            attacker.choiced = True
            attacker.move_choice = name
        #こだわりハチマキ
        if attacker.item == "Choice Band" and self.category == "Physical":
            other *= 1.5
        #こだわりメガネ
        if attacker.item == "Choice Specs" and self.category == "Special":
            other *= 1.5
        #突撃チョッキ
        if defender.item == "Assault Vest" and self.category == "Special":
            defense *= 1.5
        #しんかのきせき
        if defender.item == "Eviolite":
            defense *= 1.5
        #やけど
        if attacker.status == "burn" and self.category == "Physical":
            if attacker.ability == "Guts":
                other *= 1.5
            else:
                other /= 2.0
        #タイプ一致攻撃
        stab = 1.5 if move_type in attacker.typing else 1
        #適応力
        if attacker.ability == "Adaptability" and stab == 1.5:
            stab = 2
        #ちょすい、かんそうはだ
        if move_type == "Water" and (defender.ability == "Water Absorb" or defender.ability == "Dry Skin"):
            other *= 0
            defender.heal(0.25)
        #かんそうはだ
        if move_type == "Fire" and defender.ability == "Dry Skin":
            other *= 1.25
        #よびみず
        if move_type == "Water" and defender.ability == "Storm Drain":
            other *= 0
            defender.increase_stage('spatk', 1)
        #ちくでん
        if move_type == "Electric" and defender.ability == "Volt Absorb":
            other *= 0
            defender.heal(0.25)
        #ひらいしん
        if move_type == "Electric" and defender.ability == "Lightning Rod":
            other *= 0
            defender.increase_stage('spatk', 1)
        #電気エンジン
        if move_type == "Electric" and defender.ability == "Motor Drive":
            other *= 0
            defender.increase_stage('spe', 1)
        #もらいび
        if move_type == "Fire" and defender.ability == "Flash Fire":
            other *= 0
        #タイプ相性
        type_multipliers = [get_multiplier(x, move_type, attacker.ability=="Scrappy") for x in defender.typing]
        for x in type_multipliers:
            type *= x
        #急所
        critical = 1
        #乱数
        r = 1
        #ダメージUP
        modifier = stab * type * critical * other * r
        #ちからもち　ヨガパワー
        if attacker.ability == "Huge Power" or attacker.ability == "Pure Power":
            attack *= 2
        #ダメージ量計算
        damage = (((22.0) * attack/defense * power)/50 + 2) * modifier
        #ダメージを与える
        defender.damage(damage)
        #ハンドラ
        self.handler(gamestate, damage, who)
        #防御側の特性を元に戻す
        defender.ability = old_ability
        return damage

class HealingMove(Move):
    def __init__(self, name,
                 category=None,
                 priority=0,
                 type=None,
                 accuracy=1.0,
                 handler=void_handler,
                 healing_percent=0
                 ):
        Move.__init__(self, name,
                      category=category,
                      priority=priority,
                      type=type,
                      accuracy=accuracy,
                      handler=handler
                      )
        self.healing_percent = healing_percent

    def handle(self, gamestate, who, log=False):
        gamestate.get_team(who).primary().heal(self.healing_percent)
        self.handler(gamestate, 0, who)
        return 0
