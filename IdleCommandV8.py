# IdleCommand_v4d.py
# v4d = Endurance Progression + Readability + No Builders + No Manual Raid
# Mechanics: Gold + Uranium only; all income from troops; prestige requires ALL buildings & troops Lv20.
# UI: Larger button fonts, dark theme, responsive scaling.

import json, math, os, sys, time
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont

SAVE_PATH = "idle_command_save.json"

# --- Timing ---
AUTOSAVE_INTERVAL = 60
GAME_STEP_SECONDS  = 1.0
MAX_FRAME_DT       = 0.25
MIN_FRAME_DT       = 0.01
TIME_SCALE         = 1.0

# Uranium skip rule: 1 particle skips X minutes
URANIUM_MINUTES_PER_PARTICLE = 10

# Prestige bonuses
PRESTIGE_INCOME_MULT = 1.10   # +10% income per prestige
PRESTIGE_TIME_MULT   = 0.90   # -10% duration per prestige
PRESTIGE_URAN_RATE   = 1.05   # +5% uranium/hr per prestige

# ====== DATA ======

TROOPS_TAB = "Troops"
TABS_ORDER = ["Military Core", TROOPS_TAB, "Nuclear & Prestige"]

BUILDINGS_BY_TAB = {
    "Military Core": [
        "Command Center", "Builder Hut",
        "Barracks", "Armory", "Vehicle Plant", "War Factory",
        "Airfield", "Naval Port", "Drone Bay"
    ],
    "Nuclear & Prestige": [
        "Uranium Mine", "Nuclear Silo", "Nuclear Reactor",
        "World Treasury", "Monument of Victory"
    ],
}

# Endurance progression: higher cost growth; Builder Hut now reduces times
BUILDING_DEFS = {
    "Command Center": {"type":"booster","unlock_cmd":1,"max_level":20,
        "base_cost_gold": 500, "cost_growth": 2.00,
        "base_time_sec": 120, "time_growth": 1.55,
        "income_mult_per_level": 0.004},  # tiny global nudge per CC level

    # Reworked: global time reducer (no builders anymore)
    "Builder Hut": {"type":"booster","unlock_cmd":1,"max_level":20,
        "base_cost_gold": 200, "cost_growth": 1.65,
        "base_time_sec": 60,  "time_growth": 1.50,
        "time_reduction_per_level": 0.015},  # -1.5% per level (beyond Lv1)

    # Military chain (unlock troops & add small gold mults)
    "Barracks": {"type":"booster","unlock_cmd":1,"max_level":20,
        "base_cost_gold": 180, "cost_growth": 1.65,
        "base_time_sec": 45,  "time_growth": 1.50,
        "gold_mult_per_level": 0.003},
    "Armory": {"type":"booster","unlock_cmd":2,"max_level":20,
        "base_cost_gold": 300, "cost_growth": 1.65,
        "base_time_sec": 70,  "time_growth": 1.52,
        "gold_mult_per_level": 0.004},
    "Vehicle Plant": {"type":"booster","unlock_cmd":3,"max_level":20,
        "base_cost_gold": 450, "cost_growth": 1.65,
        "base_time_sec": 120, "time_growth": 1.55,
        "gold_mult_per_level": 0.005},
    "War Factory": {"type":"booster","unlock_cmd":4,"max_level":20,
        "base_cost_gold": 600, "cost_growth": 1.65,
        "base_time_sec": 140, "time_growth": 1.56,
        "gold_mult_per_level": 0.006},
    "Airfield": {"type":"booster","unlock_cmd":5,"max_level":20,
        "base_cost_gold": 750, "cost_growth": 1.65,
        "base_time_sec": 160, "time_growth": 1.57,
        "gold_mult_per_level": 0.0065},
    "Naval Port": {"type":"booster","unlock_cmd":6,"max_level":20,
        "base_cost_gold": 900, "cost_growth": 1.65,
        "base_time_sec": 180, "time_growth": 1.58,
        "gold_mult_per_level": 0.007},
    "Drone Bay": {"type":"booster","unlock_cmd":7,"max_level":20,
        "base_cost_gold": 1100, "cost_growth": 1.65,
        "base_time_sec": 200,  "time_growth": 1.58,
        "income_mult_per_level": 0.005},

    # Nuclear & Prestige
    "Uranium Mine": {"type":"uranium_rate","unlock_cmd":1,"max_level":20,
        "base_u_per_hour": (1.0/12.0), "rate_growth": 1.18,
        "base_cost_gold": 220, "cost_growth": 1.60,
        "base_time_sec": 60,  "time_growth": 1.50},

    "Nuclear Silo": {"type":"uranium_cap","unlock_cmd":1,"max_level":20,
        "base_cap": 50, "cap_growth": 1.35,
        "base_cost_gold": 260, "cost_growth": 1.60,
        "base_time_sec": 60,  "time_growth": 1.50},

    "Nuclear Reactor": {"type":"booster","unlock_cmd":10,"max_level":20,
        "base_cost_gold": 1200, "cost_growth": 1.65,
        "base_time_sec": 220,  "time_growth": 1.58,
        "uranium_rate_mult_per_level": 0.08},

    "World Treasury": {"type":"booster","unlock_cmd":15,"max_level":20,
        "base_cost_gold": 2000, "cost_growth": 1.65,
        "base_time_sec": 260,  "time_growth": 1.60,
        "income_mult_per_level": 0.007},

    "Monument of Victory": {"type":"booster","unlock_cmd":20,"max_level":20,
        "base_cost_gold": 3000, "cost_growth": 1.65,
        "base_time_sec": 300,  "time_growth": 1.62,
        "gold_mult_per_level": 0.012},
}

# Troops: gold-only costs; yield only if unlocked (building level requirement met)
# Endurance: cost_growth 1.55, yield growth 1.15 (income grows slower than costs)
TROOP_DEFS = {
    # Barracks / Armory (infantry line)
    "Infantry":     {"unlock_building":"Barracks","req_level":1,"base_yield":40,"growth":1.15,
                     "base_costs":{"gold":80},  "cost_growth":1.55,"base_time_sec":15,"time_growth":1.40,"max_level":20},
    "Scout":        {"unlock_building":"Barracks","req_level":2,"base_yield":80,"growth":1.15,
                     "base_costs":{"gold":160}, "cost_growth":1.55,"base_time_sec":24,"time_growth":1.42,"max_level":20},
    "Sniper":       {"unlock_building":"Armory","req_level":1,"base_yield":140,"growth":1.15,
                     "base_costs":{"gold":320}, "cost_growth":1.55,"base_time_sec":32,"time_growth":1.44,"max_level":20},
    "Ranger":       {"unlock_building":"Armory","req_level":3,"base_yield":220,"growth":1.15,
                     "base_costs":{"gold":520}, "cost_growth":1.55,"base_time_sec":45,"time_growth":1.46,"max_level":20},
    "Heavy Gunner": {"unlock_building":"Armory","req_level":5,"base_yield":360,"growth":1.15,
                     "base_costs":{"gold":900}, "cost_growth":1.55,"base_time_sec":60,"time_growth":1.48,"max_level":20},

    # Vehicles
    "Motorcycle":   {"unlock_building":"Vehicle Plant","req_level":2,"base_yield":520,"growth":1.15,
                     "base_costs":{"gold":1200}, "cost_growth":1.55,"base_time_sec":80,"time_growth":1.50,"max_level":20},
    "Jeep":         {"unlock_building":"Vehicle Plant","req_level":3,"base_yield":740,"growth":1.15,
                     "base_costs":{"gold":1700}, "cost_growth":1.55,"base_time_sec":92,"time_growth":1.51,"max_level":20},
    "APC":          {"unlock_building":"Vehicle Plant","req_level":4,"base_yield":980,"growth":1.15,
                     "base_costs":{"gold":2400}, "cost_growth":1.55,"base_time_sec":104,"time_growth":1.52,"max_level":20},
    "Tank":         {"unlock_building":"War Factory","req_level":2,"base_yield":1300,"growth":1.15,
                     "base_costs":{"gold":3600}, "cost_growth":1.55,"base_time_sec":125,"time_growth":1.54,"max_level":20},
    "Artillery":    {"unlock_building":"War Factory","req_level":4,"base_yield":1800,"growth":1.15,
                     "base_costs":{"gold":5200}, "cost_growth":1.55,"base_time_sec":145,"time_growth":1.55,"max_level":20},

    # Air
    "Helicopter":   {"unlock_building":"Airfield","req_level":2,"base_yield":2300,"growth":1.15,
                     "base_costs":{"gold":7000}, "cost_growth":1.55,"base_time_sec":140,"time_growth":1.54,"max_level":20},
    "Jet":          {"unlock_building":"Airfield","req_level":3,"base_yield":3100,"growth":1.15,
                     "base_costs":{"gold":11000}, "cost_growth":1.55,"base_time_sec":165,"time_growth":1.56,"max_level":20},
    "Bomber":       {"unlock_building":"Airfield","req_level":4,"base_yield":4000,"growth":1.15,
                     "base_costs":{"gold":16000}, "cost_growth":1.55,"base_time_sec":185,"time_growth":1.57,"max_level":20},
    "Drone":        {"unlock_building":"Drone Bay","req_level":1,"base_yield":2600,"growth":1.15,
                     "base_costs":{"gold":9000},  "cost_growth":1.55,"base_time_sec":130,"time_growth":1.54,"max_level":20},
    "Gunship":      {"unlock_building":"Drone Bay","req_level":3,"base_yield":5200,"growth":1.15,
                     "base_costs":{"gold":21000}, "cost_growth":1.55,"base_time_sec":190,"time_growth":1.58,"max_level":20},

    # Naval
    "Patrol Boat":  {"unlock_building":"Naval Port","req_level":2,"base_yield":2600,"growth":1.15,
                     "base_costs":{"gold":9000},  "cost_growth":1.55,"base_time_sec":160,"time_growth":1.55,"max_level":20},
    "Destroyer":    {"unlock_building":"Naval Port","req_level":3,"base_yield":3400,"growth":1.15,
                     "base_costs":{"gold":15000}, "cost_growth":1.55,"base_time_sec":180,"time_growth":1.57,"max_level":20},
    "Submarine":    {"unlock_building":"Naval Port","req_level":4,"base_yield":4200,"growth":1.15,
                     "base_costs":{"gold":22000}, "cost_growth":1.55,"base_time_sec":200,"time_growth":1.58,"max_level":20},
}

def clamp(v, lo, hi): return lo if v < lo else hi if v > hi else v

# ====== MODEL ======

class UpgradeTask:
    def __init__(self, total_seconds):
        self.total = max(1, int(total_seconds))
        self.remaining = self.total
    def tick(self, sec): self.remaining = max(0, self.remaining - sec)
    @property
    def done(self): return self.remaining <= 0
    @property
    def progress(self): return 0.0 if self.total<=0 else (self.total - self.remaining)/self.total

class BuildingState:
    def __init__(self, name): self.name=name; self.level=1; self.task=None
class TroopState:
    def __init__(self, name): self.name=name; self.level=1; self.task=None

class GameState:
    def __init__(self):
        self.gold=200.0
        self.uranium=0.0
        self.prestige=0
        self.command_level=1

        self.buildings={n:BuildingState(n) for tab in BUILDINGS_BY_TAB.values() for n in tab}
        self.troops={n:TroopState(n) for n in TROOP_DEFS.keys()}

        self.gold_per_min=0.0
        self.uranium_per_hour=0.0
        self.uranium_cap=50.0

        self.global_income_mult=1.0
        self.global_time_mult=1.0
        self.gold_mult=1.0
        self.uranium_rate_mult=1.0

        self._accum = 0.0
        self.last_autosave=time.time()

        self.recompute_all()

    # --- save/load ---
    def to_dict(self):
        return {
            "gold": self.gold,
            "uranium": self.uranium,
            "prestige": self.prestige,
            "command_level": self.command_level,
            "buildings": {n: {"level": b.level,
                              "task": ({"total": b.task.total, "remaining": b.task.remaining} if b.task else None)}
                          for n,b in self.buildings.items()},
            "troops": {n: {"level": t.level,
                           "task": ({"total": t.task.total, "remaining": t.task.remaining} if t.task else None)}
                       for n,t in self.troops.items()},
            "last_autosave": self.last_autosave,
        }

    def load_dict(self, d):
        self.gold = float(d.get("gold", self.gold))
        self.uranium = float(d.get("uranium", self.uranium))
        self.prestige = int(d.get("prestige", self.prestige))
        self.command_level = int(d.get("command_level", self.command_level))

        for n,bd in d.get("buildings", {}).items():
            if n in self.buildings:
                self.buildings[n].level = int(bd.get("level",1))
                t = bd.get("task")
                if t:
                    self.buildings[n].task = UpgradeTask(int(t.get("total",1)))
                    self.buildings[n].task.remaining=int(t.get("remaining",0))
                else:
                    self.buildings[n].task=None

        for n,td in d.get("troops", {}).items():
            if n in self.troops:
                self.troops[n].level = int(td.get("level",1))
                t = td.get("task")
                if t:
                    self.troops[n].task = UpgradeTask(int(t.get("total",1)))
                    self.troops[n].task.remaining=int(t.get("remaining",0))
                else:
                    self.troops[n].task=None

        self.last_autosave = float(d.get("last_autosave", time.time()))
        self.recompute_all()

    # --- defs ---
    def bdef(self, name): return BUILDING_DEFS[name]
    def tdef(self, name): return TROOP_DEFS[name]

    # --- numbers ---
    def next_building_cost(self, name):
        b=self.buildings[name]; d=self.bdef(name)
        return d["base_cost_gold"] * (d["cost_growth"] ** (b.level-1))

    def next_building_time(self, name):
        b=self.buildings[name]; d=self.bdef(name)
        t = d["base_time_sec"] * (d["time_growth"] ** (b.level-1))
        # Global time multipliers
        t *= (PRESTIGE_TIME_MULT ** self.prestige) * self.global_time_mult
        return max(1.0, t)

    def building_desc(self, name):
        b=self.buildings[name]; d=self.bdef(name); L=b.level; t=d["type"]
        if t=="uranium_rate":
            base=d["base_u_per_hour"]; g=d["rate_growth"]; r=base*(g**(L-1))
            r*= (PRESTIGE_URAN_RATE**self.prestige) * self.uranium_rate_mult
            return f"+{r:.3f} ⚛/hr"
        if t=="uranium_cap":
            base=d["base_cap"]; g=d["cap_growth"]; cap=base*(g**(L-1))
            return f"Cap {int(cap)} ⚛"
        if t=="booster": return "Passive bonus"
        return ""

    def next_troop_costs(self, name):
        ts=self.troops[name]; d=self.tdef(name); L=ts.level
        return {"gold": d["base_costs"]["gold"] * (d["cost_growth"] ** (L-1))}

    def next_troop_time(self, name):
        ts=self.troops[name]; d=self.tdef(name)
        t=d["base_time_sec"]*(d["time_growth"]**(ts.level-1))
        t*= (PRESTIGE_TIME_MULT ** self.prestige) * self.global_time_mult
        return max(1.0, t)

    def troop_unlocked(self, tname):
        d=self.tdef(tname)
        bname=d["unlock_building"]; req=d["req_level"]
        if BUILDING_DEFS[bname]["unlock_cmd"] > self.command_level:
            return False, f"🔒 Requires Command Level {BUILDING_DEFS[bname]['unlock_cmd']} to unlock {bname}"
        if self.buildings[bname].level < req:
            return False, f"🔒 Requires {bname} Lv {req}"
        return True, ""

    def troop_yield_per_min(self, name):
        ok,_ = self.troop_unlocked(name)
        if not ok: return 0.0
        ts=self.troops[name]; d=self.tdef(name)
        y=d["base_yield"]*(d["growth"]**(ts.level-1))
        y*= (PRESTIGE_INCOME_MULT**self.prestige) * self.global_income_mult * self.gold_mult
        return y

    # --- recompute ---
    def recompute_all(self):
        self.global_income_mult = 1.0
        self.global_time_mult   = 1.0
        self.gold_mult          = 1.0
        self.uranium_rate_mult  = 1.0

        for name, bs in self.buildings.items():
            d=self.bdef(name); L=bs.level; t=d["type"]
            if name=="Command Center":
                self.command_level = clamp(L,1,20)
                inc=d.get("income_mult_per_level",0.0)
                self.global_income_mult *= (1.0 + inc*(L-1))
            if t=="booster":
                if "income_mult_per_level" in d:
                    self.global_income_mult *= (1.0 + d["income_mult_per_level"]*(L-1))
                if "gold_mult_per_level" in d:
                    self.gold_mult *= (1.0 + d["gold_mult_per_level"]*(L-1))
                if "uranium_rate_mult_per_level" in d:
                    self.uranium_rate_mult *= (1.0 + d["uranium_rate_mult_per_level"]*(L-1))
                if name=="Builder Hut":
                    red = d.get("time_reduction_per_level", 0.0) * max(0, L-1)
                    self.global_time_mult *= max(0.3, 1.0 - red)  # clamp so it never hits zero

        # aggregate rates
        self.gold_per_min = 0.0
        for tname in self.troops.keys():
            self.gold_per_min += self.troop_yield_per_min(tname)

        self.uranium_per_hour = 0.0
        self.uranium_cap = 0.0
        for name, bs in self.buildings.items():
            d=self.bdef(name); L=bs.level; t=d["type"]
            if t=="uranium_rate":
                self.uranium_per_hour += d["base_u_per_hour"] * (d["rate_growth"] ** (L-1))
            elif t=="uranium_cap":
                self.uranium_cap += d["base_cap"] * (d["cap_growth"] ** (L-1))

        self.uranium_per_hour *= (PRESTIGE_URAN_RATE**self.prestige) * self.uranium_rate_mult
        self.uranium_cap = max(self.uranium_cap, 50.0)

    # --- gating / prestige ---
    def _cc_gate_all_unlocked(self):
        cc = self.command_level
        for bname, bstate in self.buildings.items():
            if bname == "Command Center": continue
            if BUILDING_DEFS[bname]["unlock_cmd"] <= cc:
                if bstate.level < cc:
                    return False, f"All unlocked buildings must reach Lv {cc} to upgrade Command Center."
        return True, ""

    def _cap_ok(self, current_level):
        return current_level < self.command_level

    def _any_active_tasks(self):
        for b in self.buildings.values():
            if b.task: return True
        for t in self.troops.values():
            if t.task: return True
        return False

    def can_prestige(self):
        if self._any_active_tasks(): return False
        for b in self.buildings.values():
            if b.level < BUILDING_DEFS[b.name]["max_level"]:
                return False
        for t in self.troops.values():
            if t.level < TROOP_DEFS[t.name]["max_level"]:
                return False
        return True

    def do_prestige(self):
        self.prestige += 1
        keep_u = self.uranium
        self.gold = 0.0
        self.uranium = min(keep_u, self.uranium_cap)
        for b in self.buildings.values(): b.level=1; b.task=None
        for t in self.troops.values(): t.level=1; t.task=None
        self.command_level=1
        self.recompute_all()

    # --- actions ---
    def try_upgrade_building(self, name):
        d=self.bdef(name); b=self.buildings[name]
        if name=="Command Center":
            ok,msg=self._cc_gate_all_unlocked()
            if not ok: return False, msg
        if self.command_level < d["unlock_cmd"]: return False, "🔒 Locked by Command Level."
        if b.task: return False, "Already upgrading."
        if b.level >= d["max_level"]: return False, "Already max level."
        if not self._cap_ok(b.level) and name!="Command Center":
            return False, f"Requires Command Center Lv {b.level+1}"

        cost = self.next_building_cost(name)
        if self.gold < cost: return False, "Not enough Gold."
        self.gold -= cost
        b.task = UpgradeTask(self.next_building_time(name))
        return True, f"Upgrading {name} to Lv {b.level+1}"

    def try_skip_building(self, name):
        b=self.buildings[name]
        if not b.task: return False, "No upgrade running."
        minutes_left = math.ceil(b.task.remaining/60.0)
        need = math.ceil(minutes_left/URANIUM_MINUTES_PER_PARTICLE)
        if self.uranium < need: return False, f"Need {need} ⚛."
        self.uranium -= need; b.task.remaining=0
        return True, f"Skipped {minutes_left} min with {need} ⚛"

    def try_upgrade_troop(self, name):
        ok,msg = self.troop_unlocked(name)
        if not ok: return False, msg
        ts=self.troops[name]; d=self.tdef(name)
        if ts.task: return False, "Already upgrading."
        if ts.level >= d["max_level"]: return False, "Already max level."
        if not self._cap_ok(ts.level): return False, f"Requires Command Center Lv {ts.level+1}"
        costs=self.next_troop_costs(name)
        if self.gold < costs["gold"]: return False, "Not enough Gold."
        self.gold -= costs["gold"]
        ts.task=UpgradeTask(self.next_troop_time(name))
        return True, f"Upgrading {name} to Lv {ts.level+1}"

    def try_skip_troop(self, name):
        ts=self.troops[name]
        if not ts.task: return False, "No upgrade running."
        minutes_left=math.ceil(ts.task.remaining/60.0)
        need=math.ceil(minutes_left/URANIUM_MINUTES_PER_PARTICLE)
        if self.uranium < need: return False, f"Need {need} ⚛."
        self.uranium -= need; ts.task.remaining=0
        return True, f"Skipped {minutes_left} min with {need} ⚛"

    # --- tick ---
    def tick_frame(self, dt):
        dt = clamp(dt, MIN_FRAME_DT, MAX_FRAME_DT) * TIME_SCALE
        self._accum += dt
        while self._accum >= GAME_STEP_SECONDS:
            self._accum -= GAME_STEP_SECONDS
            self._tick_one_second()

    def _tick_one_second(self):
        total_troop_pm = 0.0
        for tname in self.troops.keys():
            total_troop_pm += self.troop_yield_per_min(tname)
        self.gold += total_troop_pm / 60.0

        self.uranium += self.uranium_per_hour / 3600.0
        if self.uranium > self.uranium_cap: self.uranium = self.uranium_cap

        for name in list(self.buildings.keys()):
            bs=self.buildings[name]
            if bs.task:
                bs.task.tick(1.0); self._complete_building(name)
        for name in list(self.troops.keys()):
            ts=self.troops[name]
            if ts.task:
                ts.task.tick(1.0); self._complete_troop(name)

    def _complete_building(self, name):
        b=self.buildings[name]
        if b.task and b.task.done:
            b.task=None; b.level+=1
            if name=="Command Center":
                self.command_level = clamp(b.level,1,20)
            self.recompute_all(); return True
        return False

    def _complete_troop(self, name):
        t=self.troops[name]
        if t.task and t.task.done:
            t.task=None; t.level+=1
            self.recompute_all(); return True
        return False

# ====== UI ======

class BaseRow:
    @staticmethod
    def fmt_time(sec):
        if sec<=0: return "Done"
        m,s=divmod(int(sec),60); h,m=divmod(m,60)
        return f"{h}h {m}m" if h else (f"{m}m {s}s" if m else f"{s}s")

class BuildingRow:
    def __init__(self, parent, game, name, fonts):
        self.game=game; self.name=name; self.fonts=fonts
        self.frame=ttk.Frame(parent)
        self.lbl_name=ttk.Label(self.frame, text=name, font=fonts["label"], width=20, anchor="w")
        self.lbl_lvl=ttk.Label(self.frame, text="Lv.1", font=fonts["mono"], width=7, anchor="w")
        self.lbl_desc=ttk.Label(self.frame, text="", font=fonts["mono"], width=20, anchor="w")
        self.prog=ttk.Progressbar(self.frame, length=260, style="Fat.Horizontal.TProgressbar")
        self.lbl_time=ttk.Label(self.frame, text="Idle", font=fonts["mono"], width=9, anchor="center")
        self.btn_up=ttk.Button(self.frame, text="Upgrade", width=14, command=self.do_up, style="Wide.TButton")
        self.btn_skip=ttk.Button(self.frame, text="Skip ⚛", width=12, command=self.do_skip, style="Wide.TButton")
        self.lbl_cost=ttk.Label(self.frame, text="Cost: -", font=fonts["mono"], width=18, anchor="e")
        self.lbl_req=ttk.Label(self.frame, text="", font=fonts["hint"], anchor="w")

        self.lbl_name.grid(row=0, column=0, sticky="w", padx=(8,0), pady=(3,0))
        self.lbl_lvl.grid(row=0, column=1, sticky="w")
        self.lbl_desc.grid(row=0, column=2, sticky="w")
        self.prog.grid(row=0, column=3, sticky="we", padx=8)
        self.lbl_time.grid(row=0, column=4, sticky="e")
        self.btn_up.grid(row=0, column=5, padx=(8,4))
        self.btn_skip.grid(row=0, column=6, padx=(4,8))
        self.lbl_cost.grid(row=0, column=7, sticky="e", padx=(0,8))
        self.lbl_req.grid(row=1, column=0, columnspan=8, sticky="w", padx=(8,0), pady=(0,6))
        self.frame.columnconfigure(3, weight=1)

    def do_up(self):
        ok,msg=self.game.try_upgrade_building(self.name)
        if not ok: messagebox.showinfo("Upgrade", msg)

    def do_skip(self):
        ok,msg=self.game.try_skip_building(self.name)
        if not ok: messagebox.showinfo("Skip", msg)

    def refresh(self):
        bs=self.game.buildings[self.name]; d=BUILDING_DEFS[self.name]
        self.lbl_lvl.config(text=f"Lv.{bs.level}")
        self.lbl_desc.config(text=self.game.building_desc(self.name))

        req_text=""
        if d["unlock_cmd"] > self.game.command_level:
            req_text=f"🔒 Requires Command Level {d['unlock_cmd']}"
        elif self.name=="Command Center":
            ok,msg=self.game._cc_gate_all_unlocked()
            if not ok: req_text=f"🔒 {msg}"
        elif bs.level >= self.game.command_level:
            req_text=f"🔒 Requires Command Center Lv {bs.level+1}"
        self.lbl_req.config(text=req_text)

        if bs.task:
            self.prog["value"]=bs.task.progress*100
            self.lbl_time.config(text=BaseRow.fmt_time(bs.task.remaining))
            self.btn_skip.state(["!disabled"]); self.btn_up.state(["disabled"])
        else:
            self.prog["value"]=0
            maxed = bs.level >= d["max_level"]
            self.lbl_time.config(text="MAX" if maxed else "Idle")
            self.btn_skip.state(["disabled"])
            disabled = (d["unlock_cmd"]>self.game.command_level) or maxed or (bs.level >= self.game.command_level and self.name!="Command Center")
            self.btn_up.state(["disabled"] if disabled else ["!disabled"])

        self.lbl_cost.config(text=f"Cost: {int(self.game.next_building_cost(self.name))} Gold")

class TroopRow:
    def __init__(self, parent, game, name, fonts):
        self.game=game; self.name=name; self.fonts=fonts
        self.frame=ttk.Frame(parent)
        self.lbl_name=ttk.Label(self.frame, text=name, font=fonts["label"], width=20, anchor="w")
        self.lbl_lvl=ttk.Label(self.frame, text="Lv.1", font=fonts["mono"], width=7, anchor="w")
        self.lbl_yield=ttk.Label(self.frame, text="", font=fonts["mono"], width=20, anchor="w")
        self.prog=ttk.Progressbar(self.frame, length=260, style="Fat.Horizontal.TProgressbar")
        self.lbl_time=ttk.Label(self.frame, text="Idle", font=fonts["mono"], width=9, anchor="center")
        self.btn_up=ttk.Button(self.frame, text="Upgrade", width=14, command=self.do_up, style="Wide.TButton")
        self.btn_skip=ttk.Button(self.frame, text="Skip ⚛", width=12, command=self.do_skip, style="Wide.TButton")
        self.lbl_cost=ttk.Label(self.frame, text="Cost: -", font=fonts["mono"], width=18, anchor="e")
        self.lbl_req=ttk.Label(self.frame, text="", font=fonts["hint"], anchor="w")

        self.lbl_name.grid(row=0, column=0, sticky="w", padx=(8,0), pady=(3,0))
        self.lbl_lvl.grid(row=0, column=1, sticky="w")
        self.lbl_yield.grid(row=0, column=2, sticky="w")
        self.prog.grid(row=0, column=3, sticky="we", padx=8)
        self.lbl_time.grid(row=0, column=4, sticky="e")
        self.btn_up.grid(row=0, column=5, padx=(8,4))
        self.btn_skip.grid(row=0, column=6, padx=(4,8))
        self.lbl_cost.grid(row=0, column=7, sticky="e", padx=(0,8))
        self.lbl_req.grid(row=1, column=0, columnspan=8, sticky="w", padx=(8,0), pady=(0,6))
        self.frame.columnconfigure(3, weight=1)

    def do_up(self):
        ok,msg=self.game.try_upgrade_troop(self.name)
        if not ok: messagebox.showinfo("Upgrade", msg)

    def do_skip(self):
        ok,msg=self.game.try_skip_troop(self.name)
        if not ok: messagebox.showinfo("Skip", msg)

    def refresh(self):
        ts=self.game.troops[self.name]; d=TROOP_DEFS[self.name]
        y=self.game.troop_yield_per_min(self.name)
        self.lbl_lvl.config(text=f"Lv.{ts.level}")
        self.lbl_yield.config(text=f"+{y:.1f} Gold/min")

        ok,msg=self.game.troop_unlocked(self.name)
        req_text = "" if ok else msg
        if ts.level >= self.game.command_level:
            req_text = f"🔒 Requires Command Center Lv {ts.level+1}"
        self.lbl_req.config(text=req_text)

        if ts.task:
            self.prog["value"]=ts.task.progress*100
            self.lbl_time.config(text=BaseRow.fmt_time(ts.task.remaining))
            self.btn_up.state(["disabled"]); self.btn_skip.state(["!disabled"])
        else:
            self.prog["value"]=0
            maxed = ts.level >= d["max_level"]
            self.lbl_time.config(text="MAX" if maxed else "Idle")
            self.btn_skip.state(["disabled"])
            disabled = (not ok) or maxed or (ts.level >= self.game.command_level)
            self.btn_up.state(["disabled"] if disabled else ["!disabled"])

        costs=self.game.next_troop_costs(self.name)
        self.lbl_cost.config(text=f"Cost: {int(costs['gold'])} Gold")

# ====== APP ======

class App:
    def __init__(self, root):
        self.root=root
        self.root.title("Idle Command — v4d (Endurance)")

        if sys.platform.startswith("win"):
            try:
                from ctypes import windll
                windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass

        self.style=ttk.Style(root)
        self.enable_dark_mode()

        # Bigger baseline → ensures large fonts even in small windows
        self.base_width=1100
        self.base_height=650
        self.fonts=self.make_fonts(scale=1.6)   # bigger buttons/tabs
        self.pad_scale=1.6

        self.game=GameState()
        self.load_game()

        # Header
        hdr=ttk.Frame(root, padding=(10,10)); hdr.pack(fill="x")
        self.lbl_title=ttk.Label(hdr, text="⚙️  IDLE COMMAND", font=self.fonts["title"])
        self.lbl_title.pack(side="left")

        right=ttk.Frame(hdr); right.pack(side="right")
        ttk.Button(right, text="Save", command=self.save_game, style="Wide.TButton").pack(side="right", padx=self.scaled(8))
        self.btn_prestige=ttk.Button(right, text="Prestige", command=self.do_prestige, style="Wide.TButton")
        self.btn_prestige.pack(side="right", padx=self.scaled(8))

        # CC status
        cc=ttk.Frame(root, padding=(10,0)); cc.pack(fill="x")
        self.lbl_cc=ttk.Label(cc, text="", font=self.fonts["mono_bold"])
        self.lbl_cc.pack(side="left")

        # Resources
        res=ttk.Frame(root, padding=(10,6)); res.pack(fill="x")
        self.lbl_res=ttk.Label(res, text="", font=self.fonts["mono"])
        self.lbl_res.pack(side="left")

        # Tabs
        self.nb=ttk.Notebook(root, style="Big.TNotebook"); self.nb.pack(fill="both", expand=True, padx=self.scaled(8), pady=self.scaled(8))
        self.tab_frames={}; self.rows_by_tab={}

        for tab_name in TABS_ORDER:
            frame=ttk.Frame(self.nb)
            self.nb.add(frame, text=tab_name)
            self.tab_frames[tab_name]=frame

        self.rows_by_tab["Military Core"] = self.make_building_scroller(
            self.tab_frames["Military Core"], BUILDINGS_BY_TAB["Military Core"]) 
        self.rows_by_tab["Nuclear & Prestige"] = self.make_building_scroller(
            self.tab_frames["Nuclear & Prestige"], BUILDINGS_BY_TAB["Nuclear & Prestige"]) 
        self.rows_by_tab[TROOPS_TAB] = self.make_troop_scroller(
            self.tab_frames[TROOPS_TAB], list(TROOP_DEFS.keys()))

        foot=ttk.Frame(root, padding=self.scaled(10)); foot.pack(fill="x")
        self.lbl_status=ttk.Label(foot, text="", font=self.fonts["mono"])
        self.lbl_status.pack(side="left")
        ttk.Button(foot, text="Exit", command=self.on_exit, style="Wide.TButton").pack(side="right")

        # Start centered
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        w, h = min(1600, sw-100), min(950, sh-120)
        x, y = (sw - w)//2, (sh - h)//2
        root.geometry(f"{w}x{h}+{x}+{y}")

        self._resize_debounce=None
        self.root.bind("<Configure>", self.on_configure)

        self._last_time=time.time()
        self.loop()
        self.ui_refresh()

    # ---- THEME & FONTS ----
    def enable_dark_mode(self):
        bg="#171717"; fg="#e9f2ec"; acc="#43ffd7"
        self.root.configure(bg=bg)
        try: self.style.theme_use("clam")
        except Exception: pass

        # Base
        self.style.configure(".", background=bg, foreground=fg)
        self.style.configure("TFrame", background=bg)
        self.style.configure("TLabel", background=bg, foreground=fg)
        # Bigger, wider buttons
        self.style.configure("Wide.TButton", background="#2b2b2b", foreground=fg, padding=(16,12))
        self.style.map("Wide.TButton", background=[("active","#343434")])

        # Tabs larger + bold
        self.style.configure("Big.TNotebook", background=bg)
        self.style.configure("TNotebook.Tab", background="#242424", foreground=fg, padding=(18,12))
        self.style.map("TNotebook.Tab", background=[("selected","#333333")])

        # Thicker progress bar
        self.style.layout("Fat.Horizontal.TProgressbar",
            [('Horizontal.Progressbar.trough',
              {'children': [('Horizontal.Progressbar.pbar', {'side': 'left', 'sticky': 'ns'})],
               'sticky': 'nswe'})])
        self.style.configure("Fat.Horizontal.TProgressbar", troughcolor="#0f0f0f", background=acc, thickness=14)

    def make_fonts(self, scale: float):
        # Large defaults; clamps prevent too-small text
        def sz(base): return max(int(round(base*scale)), 12)
        # Prefer Segoe/Consolas; fallback to Arial/Courier New
        title_family = "Segoe UI" if "Segoe UI" in tkfont.families() else "Arial"
        mono_family  = "Consolas" if "Consolas" in tkfont.families() else "Courier New"
        label_family = title_family

        fonts = {
            "title": tkfont.Font(family=title_family, size=max(int(round(20*scale)), 18), weight="bold"),
            "label": tkfont.Font(family=label_family, size=sz(14)),
            "mono":  tkfont.Font(family=mono_family,  size=sz(14)),
            "mono_bold": tkfont.Font(family=mono_family, size=max(int(round(15*scale)), 14), weight="bold"),
            "hint":  tkfont.Font(family=label_family, size=max(int(round(12*scale)), 12), slant="italic"),
            "tab":   tkfont.Font(family=label_family, size=max(int(round(14*scale)), 13), weight="bold"),
        }
        try:
            self.style.configure("TNotebook.Tab", font=fonts["tab"])
        except Exception:
            pass
        return fonts

    def scaled(self, v):  return int(round(v*self.pad_scale))

    def on_configure(self, event):
        if self._resize_debounce: self.root.after_cancel(self._resize_debounce)
        self._resize_debounce = self.root.after(60, self.apply_responsive_scale)

    def apply_responsive_scale(self):
        w = max(self.root.winfo_width(), 720)
        h = max(self.root.winfo_height(), 420)
        scale_w = w / self.base_width
        scale_h = h / self.base_height
        # Keep things big: base minimum scale 1.5
        scale = max(1.5, min(scale_w, scale_h, 2.6))
        self.fonts = self.make_fonts(scale)
        self.pad_scale = scale

        # Update top-level font assignments
        self.lbl_title.config(font=self.fonts["title"])
        self.lbl_cc.config(font=self.fonts["mono_bold"])
        self.lbl_res.config(font=self.fonts["mono"])
        self.lbl_status.config(font=self.fonts["mono"])

    # ---- Scrollers ----
    def make_building_scroller(self, parent, names):
        outer=ttk.Frame(parent); outer.pack(fill="both", expand=True)
        canvas=tk.Canvas(outer, highlightthickness=0, bg="#171717")
        sb=ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        frame=ttk.Frame(canvas)
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        rows=[]
        for n in names:
            row=BuildingRow(frame, self.game, n, self.fonts)
            row.frame.pack(fill="x", pady=self.scaled(3), padx=self.scaled(6))
            rows.append(row)
        return rows

    def make_troop_scroller(self, parent, names):
        outer=ttk.Frame(parent); outer.pack(fill="both", expand=True)
        canvas=tk.Canvas(outer, highlightthickness=0, bg="#171717")
        sb=ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        frame=ttk.Frame(canvas)
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        rows=[]
        for n in names:
            row=TroopRow(frame, self.game, n, self.fonts)
            row.frame.pack(fill="x", pady=self.scaled(3), padx=self.scaled(6))
            rows.append(row)
        return rows

    # ---- Loops ----
    def loop(self):
        now=time.time()
        dt = now - getattr(self, "_last_time", now)
        self._last_time = now
        self.game.tick_frame(dt)

        if time.time() - self.game.last_autosave >= AUTOSAVE_INTERVAL:
            self.save_game(auto=True)
            self.game.last_autosave = time.time()

        self.root.after(16, self.loop)

    def ui_refresh(self):
        self.refresh_all()
        self.root.after(120, self.ui_refresh)

    def refresh_all(self):
        self.game.recompute_all()
        g=self.game

        self.lbl_cc.config(text=(f"Command Center Lv {g.command_level}  |  "
                                 f"Prestige {g.prestige}"))

        self.lbl_res.config(text=(f"Gold {int(g.gold)}  |  Uranium {int(g.uranium)}/{int(g.uranium_cap)}"))

        inc=(f"Income/min → Gold {g.gold_per_min:.1f}  |  Uranium {g.uranium_per_hour:.3f}/hr")
        self.lbl_status.config(text=inc)

        if self.game.can_prestige(): self.btn_prestige.state(["!disabled"])
        else: self.btn_prestige.state(["disabled"])

        for rows in self.rows_by_tab.values():
            for r in rows:
                # apply current fonts
                if isinstance(r, BuildingRow) or isinstance(r, TroopRow):
                    r.lbl_name.config(font=self.fonts["label"])
                    r.lbl_lvl.config(font=self.fonts["mono"])
                    r.lbl_time.config(font=self.fonts["mono"])
                    if hasattr(r, "lbl_desc"): r.lbl_desc.config(font=self.fonts["mono"])
                    if hasattr(r, "lbl_yield"): r.lbl_yield.config(font=self.fonts["mono"])
                    r.lbl_cost.config(font=self.fonts["mono"])
                    r.lbl_req.config(font=self.fonts["hint"])
                r.refresh()

    # ---- Actions ----
    def save_game(self, auto=False):
        try:
            with open(SAVE_PATH,"w",encoding="utf-8") as f:
                json.dump(self.game.to_dict(), f, indent=2)
            if not auto:
                messagebox.showinfo("Save", f"Saved to {SAVE_PATH}")
        except Exception as e:
            if not auto:
                messagebox.showerror("Save Error", str(e))

    def load_game(self):
        if os.path.exists(SAVE_PATH):
            try:
                with open(SAVE_PATH,"r",encoding="utf-8") as f:
                    data=json.load(f)
                self.game.load_dict(data)
            except Exception:
                pass

    def do_prestige(self):
        if not self.game.can_prestige():
            messagebox.showinfo("Prestige","All buildings and all troops must be Lv 20 and no upgrades running.")
            return
        if messagebox.askyesno("Prestige", "Reset all to Lv 1 and gain permanent bonuses (+10% income, -10% time, +5% uranium/hr)?"):
            self.game.do_prestige()
            messagebox.showinfo("Prestige", f"Prestige #{self.game.prestige} complete.")

    def on_exit(self):
        self.save_game(auto=True); self.root.destroy()

def main():
    root=tk.Tk()
    app=App(root)
    root.protocol("WM_DELETE_WINDOW", app.on_exit)
    root.mainloop()

if __name__=="__main__":
    main()
