"""Campaign story system for EpicAscii - CYOA narrative between battles."""

CAMPAIGN = {
    # -- First battle: thrown straight in, no choice --
    'first_blood': {
        'type': 'battle',
        'title': 'First Blood',
        'briefing': "The horns sound. You are shoved into the front rank. Stay alive.",
        'terrain': 'open_plains',
        'blue_army': {'militia': 12, 'swordsman': 8, 'archer': 5},
        'red_army': {'militia': 10, 'swordsman': 6, 'archer': 3},
        'red_commander': True,
        'loot_tier': 1,
        'next': 'after_first_blood',
    },

    'after_first_blood': {
        'type': 'story',
        'title': 'The Aftermath',
        'text': (
            "You survived. Most didn't.\n\n"
            "The field is a carpet of bodies. Crows are already circling. "
            "You wipe blood from your face -- not all of it yours.\n\n"
            "Commander Aldric rides past, surveying the carnage. He doesn't know "
            "your name. You're just another body that's still breathing.\n\n"
            "Word comes down: the Crimson Host has a main force twice this size, "
            "marching from the east. Your regiment must decide what to do next."
        ),
        'choices': [
            {'label': 'Volunteer to scout ahead of the army', 'next': 'battle_1_scout'},
            {'label': 'March with the main body', 'next': 'battle_1_main'},
            {'label': 'Help the quartermaster salvage supplies from the dead', 'next': 'battle_1_supplies'},
        ],
    },

    'battle_1_scout': {
        'type': 'battle',
        'title': 'Skirmish at the Outpost',
        'briefing': "Your scouting party stumbles upon an enemy outpost. They've spotted you -- fight!",
        'terrain': 'forest_edge',
        'blue_army': {'swordsman': 10, 'archer': 5, 'scout': 5},
        'red_army': {'militia': 12, 'swordsman': 6, 'archer': 3},
        'red_commander': True,
        'loot_tier': 1,
        'next': 'after_battle_1',
    },

    'battle_1_main': {
        'type': 'battle',
        'title': 'The Open Field',
        'briefing': "You march with the main army and meet the enemy on open ground. Battle lines form!",
        'terrain': 'open_plains',
        'blue_army': {'swordsman': 15, 'archer': 8, 'knight': 3, 'pikeman': 4},
        'red_army': {'militia': 15, 'swordsman': 10, 'archer': 5, 'knight': 2},
        'red_commander': True,
        'loot_tier': 1,
        'next': 'after_battle_1',
    },

    'battle_1_supplies': {
        'type': 'battle',
        'title': 'Ambush on the Road',
        'briefing': "While fetching supplies, your convoy is ambushed! Defend the wagons!",
        'terrain': 'ambush',
        'blue_army': {'swordsman': 8, 'archer': 4, 'pikeman': 3},
        'red_army': {'scout': 10, 'archer': 8, 'swordsman': 5},
        'red_commander': True,
        'loot_tier': 2,  # Better loot for harder fight
        'next': 'after_battle_1',
    },

    'after_battle_1': {
        'type': 'story',
        'title': 'The Aftermath',
        'text': (
            "The dust settles. Bodies litter the ground. Your side has won, but at a cost.\n\n"
            "As you catch your breath, a wounded enemy soldier gasps out a warning: "
            "\"You fools... the main host is twice what you think. General Korrath "
            "is bringing siege engines from the north.\"\n\n"
            "Commander Aldric gathers the officers. \"We need to decide our next move.\""
        ),
        'choices': [
            {'label': 'Press the attack -- strike their camp before reinforcements arrive', 'next': 'battle_2_assault'},
            {'label': 'Set up a defensive position and dig in', 'next': 'battle_2_defense'},
            {'label': 'Send riders to request reinforcements from Ironhold', 'next': 'battle_2_delay'},
        ],
    },

    'battle_2_assault': {
        'type': 'battle',
        'title': 'Assault on the Crimson Camp',
        'briefing': "You storm the enemy camp before dawn. Catch them while they sleep!",
        'terrain': 'fortified_camp',
        'blue_army': {'swordsman': 18, 'archer': 8, 'knight': 5, 'scout': 4},
        'red_army': {'militia': 10, 'swordsman': 12, 'archer': 8, 'knight': 3, 'pikeman': 5},
        'red_commander': True,
        'loot_tier': 2,
        'next': 'after_battle_2',
    },

    'battle_2_defense': {
        'type': 'battle',
        'title': 'Hold the Line',
        'briefing': "The enemy charges your prepared positions. Hold the trenches!",
        'terrain': 'hill_assault',
        'blue_army': {'swordsman': 15, 'archer': 10, 'pikeman': 8, 'knight': 2},
        'red_army': {'swordsman': 20, 'archer': 6, 'knight': 5, 'militia': 15, 'war_mage': 2},
        'red_commander': True,
        'loot_tier': 2,
        'next': 'after_battle_2',
    },

    'battle_2_delay': {
        'type': 'battle',
        'title': 'Fighting Retreat at the River',
        'briefing': "You must hold the river crossing until reinforcements arrive!",
        'terrain': 'river_crossing',
        'blue_army': {'swordsman': 12, 'archer': 8, 'pikeman': 6},
        'red_army': {'swordsman': 15, 'scout': 10, 'archer': 6, 'knight': 4},
        'red_commander': True,
        'loot_tier': 2,
        'next': 'after_battle_2',
    },

    'after_battle_2': {
        'type': 'story',
        'title': 'Drums in the Distance',
        'text': (
            "Another victory, but your forces are bloodied and weary. "
            "The men share what food remains around guttering campfires.\n\n"
            "At midnight, the sentries report: war drums. Thousands of them. "
            "General Korrath's main army has arrived, and they outnumber you three to one.\n\n"
            "Commander Aldric's face is grim. \"This is it. Tomorrow decides everything. "
            "How we fight this battle will determine the fate of the realm.\""
        ),
        'choices': [
            {'label': 'Make a desperate charge at their general -- cut off the head', 'next': 'battle_3_charge'},
            {'label': 'Use the terrain -- lure them into the forest', 'next': 'battle_3_forest'},
            {'label': 'Make a last stand on the hilltop', 'next': 'battle_3_laststand'},
        ],
    },

    'battle_3_charge': {
        'type': 'battle',
        'title': 'The Final Charge',
        'briefing': "All or nothing. Your army charges straight at General Korrath. Kill the commander and the Host breaks!",
        'terrain': 'open_plains',
        'blue_army': {'knight': 8, 'swordsman': 15, 'archer': 6, 'pikeman': 4, 'scout': 3},
        'red_army': {'swordsman': 25, 'archer': 12, 'knight': 8, 'pikeman': 10, 'war_mage': 3, 'militia': 15},
        'red_commander': True,
        'loot_tier': 3,
        'next': 'after_battle_3',
    },

    'battle_3_forest': {
        'type': 'battle',
        'title': 'The Forest Trap',
        'briefing': "You lure the Host into dense forest where their numbers count for less.",
        'terrain': 'ambush',
        'blue_army': {'scout': 10, 'archer': 12, 'swordsman': 10, 'knight': 3},
        'red_army': {'swordsman': 20, 'militia': 20, 'archer': 8, 'knight': 5, 'war_mage': 2},
        'red_commander': True,
        'loot_tier': 3,
        'next': 'after_battle_3',
    },

    'battle_3_laststand': {
        'type': 'battle',
        'title': 'Last Stand on Ashridge',
        'briefing': "Your army forms a ring on the hilltop. If you fall here, you fall with honor.",
        'terrain': 'hill_assault',
        'blue_army': {'pikeman': 10, 'swordsman': 12, 'archer': 10, 'knight': 5},
        'red_army': {'swordsman': 30, 'archer': 10, 'knight': 8, 'militia': 20, 'war_mage': 4},
        'red_commander': True,
        'loot_tier': 3,
        'next': 'after_battle_3',
    },

    'after_battle_3': {
        'type': 'story',
        'title': 'Victory... or What Remains',
        'text': (
            "Against all odds, the Crimson Host is broken. General Korrath's banner "
            "falls, and his army scatters into the Ashlands.\n\n"
            "You stand among the survivors, bloodied but unbowed. Of the hundreds who "
            "marched from Ironhold, only a handful remain.\n\n"
            "Commander Aldric finds you. His armor is dented, his sword notched. "
            "\"You fought well today. The realm will remember what happened here.\"\n\n"
            "He reaches into his cloak and pulls out a worn medal. "
            "\"For valor beyond the call. You've earned this.\"\n\n"
            "The long march home begins. But you know in your bones -- "
            "this was only the first war."
        ),
        'choices': [
            {'label': 'Continue the campaign... (restart with your character)', 'next': 'intro'},
        ],
    },
}


class Campaign:
    def __init__(self):
        self.current_node_id = 'first_blood'
        self.battles_won = 0

    def get_current_node(self):
        return CAMPAIGN[self.current_node_id]

    def advance(self, choice_idx=0):
        """Apply a choice and return the next node id."""
        node = CAMPAIGN[self.current_node_id]
        if node['type'] == 'story':
            choices = node.get('choices', [])
            if 0 <= choice_idx < len(choices):
                self.current_node_id = choices[choice_idx]['next']
            elif choices:
                self.current_node_id = choices[0]['next']
        elif node['type'] == 'battle':
            self.battles_won += 1
            self.current_node_id = node['next']
        return self.current_node_id

    def get_battle_config(self):
        """Get the current node as a battle config (only valid if type=='battle')."""
        node = CAMPAIGN[self.current_node_id]
        assert node['type'] == 'battle', f"Node {self.current_node_id} is not a battle"
        return node
