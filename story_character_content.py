"""Authored character-specific story content frozen from the design workbook.

These records are content declarations, not executable cards.  A character card
is promoted into ``STORY_CARDS`` only after its effects have an authoritative
reducer and tests.
"""

STORY_CHARACTER_CARD_DESIGNS = {
    "mage_basic": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u57fa\u672c",
            "en": "Magic Basic"
        },
        "cost_e": 1,
        "cost_m": 2,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "",
        "base_text": "\u5bf9\u76ee\u6807\u9020\u621013D",
        "base_text_en": "Deal 13 D to the target",
        "upgrade_text": "\u5bf9\u76ee\u6807\u9020\u621018D",
        "upgrade_text_en": "Deal 18 D to the target",
        "rarity": "starter",
        "authored_rarity": "\u57fa\u7840",
        "implementation_status": "authored"
    },
    "mage_orange": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u6a59\u5b50",
            "en": "Magic Orange"
        },
        "cost_e": 0,
        "cost_m": 1,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "\u56de\u8f6c",
        "base_text": "\u5bf9\u76ee\u6807\u9020\u62105D\uff1b\u5c06\u6b64\u724c\u7f6e\u4e8e\u62bd\u724c\u5806\u9876",
        "base_text_en": "Deal 5 D to the target; put this card on top of the draw pile",
        "upgrade_text": "\u5bf9\u76ee\u6807\u9020\u62107D\uff1b\u5c06\u6b64\u724c\u7f6e\u4e8e\u62bd\u724c\u5806\u9876",
        "upgrade_text_en": "Deal 7 D to the target; put this card on top of the draw pile",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_coral": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u73ca\u745a",
            "en": "Magic Coral"
        },
        "cost_e": 1,
        "cost_m": 2,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "\u653e\u9010",
        "base_text": "\u5bf9\u76ee\u6807\u9020\u621017D\uff1b\u5c062\u5f20\u5e26\u6709\u9b54\u529b\u8fc5\u63771\u4e0e\u865a\u65e0\u7684\u9b54\u6cd5\u73ca\u745a\u7f6e\u4e8e\u62bd\u724c\u5806\u9876",
        "base_text_en": "Deal 17 D to the target; put 2 copies of Magic Coral with Magic Swift 1 and Void on top of the draw pile",
        "upgrade_text": "\u5bf9\u76ee\u6807\u9020\u621022D\uff1b\u5c062\u5f20\u5e26\u6709\u9b54\u529b\u8fc5\u63771\u7684\u9b54\u6cd5\u73ca\u745a+\u7f6e\u4e8e\u62bd\u724c\u5806\u9876",
        "upgrade_text_en": "Deal 22 D to the target; put 2 upgraded copies of Magic Coral with Magic Swift 1 on top of the draw pile",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_leaf": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u53f6",
            "en": "Magic Leaf"
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u81ea\u5df1\u56de\u5408\u5f00\u59cb\u65f6\uff0c\u56de\u590d1M",
        "base_text_en": "At the start of your turn, recover 1 M",
        "upgrade_text": "\u81ea\u5df1\u56de\u5408\u5f00\u59cb\u65f6\uff0c\u56de\u590d1M",
        "upgrade_text_en": "At the start of your turn, recover 1 M",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_compass": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u6307\u5357\u9488",
            "en": "Magic Compass"
        },
        "cost_e": 0,
        "cost_m": 1,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "\u653e\u9010",
        "base_text": "\u4ece\u62bd\u724c\u5806\u6216\u5f03\u724c\u5806\u4e2d\u9009\u62e91\u5f20\u724c\u52a0\u5165\u624b\u724c",
        "base_text_en": "Choose 1 card from your draw or discard pile and add it to your hand",
        "upgrade_text": "\u4ece\u62bd\u724c\u5806\u6216\u5f03\u724c\u5806\u4e2d\u9009\u62e91\u5f20\u724c\u52a0\u5165\u624b\u724c",
        "upgrade_text_en": "Choose 1 card from your draw or discard pile and add it to your hand",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_fries": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u85af\u6761",
            "en": "Magic Fries"
        },
        "cost_e": 1,
        "cost_m": 2,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "\u653e\u9010",
        "base_text": "\u56de\u590d\u81ea\u5df17H",
        "base_text_en": "Recover 7 H",
        "upgrade_text": "\u56de\u590d\u81ea\u5df110H",
        "upgrade_text_en": "Recover 10 H",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_coffee": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u5496\u5561",
            "en": "Magic Coffee"
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "\u653e\u9010",
        "base_text": "\u56de\u590d\u81ea\u5df14M",
        "base_text_en": "Recover 4 M",
        "upgrade_text": "\u56de\u590d\u81ea\u5df15M",
        "upgrade_text_en": "Recover 5 M",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_blood_blade": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u8840\u5203",
            "en": "Magic Blood Blade"
        },
        "cost_e": 0,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "\u56de\u8f6c",
        "base_text": "\u56de\u590d\u81ea\u5df12M\uff1b\u81ea\u5df1\u83b7\u5f971\u5c42\u7834\u635f\uff1b\u5c06\u6b64\u724c\u7f6e\u4e8e\u62bd\u724c\u5806\u9876",
        "base_text_en": "Recover 2 M; gain 1 Broken; put this card on top of your draw pile",
        "upgrade_text": "\u56de\u590d\u81ea\u5df13M\uff1b\u81ea\u5df1\u83b7\u5f971\u5c42\u7834\u635f\uff1b\u5c06\u6b64\u724c\u7f6e\u4e8e\u62bd\u724c\u5806\u9876",
        "upgrade_text_en": "Recover 3 M; gain 1 Broken; put this card on top of your draw pile",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_cotton": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u68c9\u82b1",
            "en": "Magic Cotton"
        },
        "cost_e": 1,
        "cost_m": 1,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u5c06\u81ea\u8eab\u7684\u9b54\u529b\u62a4\u76fe\u8bbe\u4e3a4",
        "base_text_en": "Set your Magic Shield to 4",
        "upgrade_text": "\u5c06\u81ea\u8eab\u7684\u9b54\u529b\u62a4\u76fe\u8bbe\u4e3a4",
        "upgrade_text_en": "Set your Magic Shield to 4",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_sunflower": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u5411\u65e5\u8475",
            "en": "Magic Sunflower"
        },
        "cost_e": 1,
        "cost_m": 1,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u6bcf\u5f53\u81ea\u5df1\u7d2f\u8ba1\u6d88\u80172E\uff0c\u56de\u590d1M",
        "base_text_en": "Whenever you spend 2 E in total, recover 1 M",
        "upgrade_text": "\u6bcf\u5f53\u81ea\u5df1\u7d2f\u8ba1\u6d88\u80172E\uff0c\u56de\u590d1M",
        "upgrade_text_en": "Whenever you spend 2 E in total, recover 1 M",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_quantum": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u91cf\u5b50",
            "en": "Magic Quantum"
        },
        "cost_e": 2,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "\u865a\u65e0\uff0c\u653e\u9010",
        "base_text": "\u672c\u56de\u5408\u5185\uff0c\u4f60\u6240\u6709\u5361\u724c\u7684E\u4e0eM\u6d88\u8017\u4e92\u6362",
        "base_text_en": "This turn, swap the E and M costs of all your cards",
        "upgrade_text": "\u79fb\u9664\u865a\u65e0\uff1b\u672c\u56de\u5408\u5185\uff0c\u4f60\u6240\u6709\u5361\u724c\u7684E\u4e0eM\u6d88\u8017\u4e92\u6362",
        "upgrade_text_en": "Remove Void; this turn, swap the E and M costs of all your cards",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_wing": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u7fc5\u8180",
            "en": "Magic Wing"
        },
        "cost_e": 1,
        "cost_m": 2,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "",
        "base_text": "\u5bf9\u76ee\u6807\u9020\u62109D\uff1b\u6d88\u8017\u81f3\u591a4M\uff0c\u6bcf\u6d88\u80171M\u5219\u989d\u5916\u653b\u51fb1\u6b21",
        "base_text_en": "Deal 9 D to the target; spend up to 4 M, with 1 extra hit per M spent",
        "upgrade_text": "\u5bf9\u76ee\u6807\u9020\u621012D\uff1b\u6d88\u8017\u81f3\u591a4M\uff0c\u6bcf\u6d88\u80171M\u5219\u989d\u5916\u653b\u51fb1\u6b21",
        "upgrade_text_en": "Deal 12 D to the target; spend up to 4 M, with 1 extra hit per M spent",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_bone": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u9aa8\u5934",
            "en": "Magic Bone"
        },
        "cost_e": 0,
        "cost_m": 3,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "",
        "base_text": "\u5bf9\u76ee\u6807\u9020\u62109D\uff1b\u81ea\u5df1\u83b7\u5f976S",
        "base_text_en": "Deal 9 D to the target; gain 6 S",
        "upgrade_text": "\u5bf9\u76ee\u6807\u9020\u621012D\uff1b\u81ea\u5df1\u83b7\u5f978S",
        "upgrade_text_en": "Deal 12 D to the target; gain 8 S",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_dahlia": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u5927\u4e3d\u82b1",
            "en": "Magic Dahlia"
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u56de\u590d\u81ea\u5df11M\uff1b\u83b7\u5f973\u5c42\u9b54\u529b\u56de\u590d\uff0c\u81ea\u5df1\u56de\u5408\u5f00\u59cb\u65f6\u56de\u590d1M\u5e76\u51cf\u5c111\u5c42",
        "base_text_en": "Recover 1 M; gain 3 Magic Recovery stacks: recover 1 M at the start of your turn, then lose 1 stack",
        "upgrade_text": "\u56de\u590d\u81ea\u5df11M\uff1b\u83b7\u5f974\u5c42\u9b54\u529b\u56de\u590d\uff0c\u81ea\u5df1\u56de\u5408\u5f00\u59cb\u65f6\u56de\u590d1M\u5e76\u51cf\u5c111\u5c42",
        "upgrade_text_en": "Recover 1 M; gain 4 Magic Recovery stacks: recover 1 M at the start of your turn, then lose 1 stack",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_soil": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u571f",
            "en": "Magic Soil"
        },
        "cost_e": 0,
        "cost_m": 4,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "\u653e\u9010",
        "base_text": "\u81ea\u5df1\u83b7\u5f9732S\uff1b\u81ea\u5df1\u83b7\u5f971\u5c42\u8d85\u8f7d",
        "base_text_en": "Gain 32 S; gain 1 Overload",
        "upgrade_text": "\u81ea\u5df1\u83b7\u5f9740S\uff1b\u81ea\u5df1\u83b7\u5f971\u5c42\u8d85\u8f7d",
        "upgrade_text_en": "Gain 40 S; gain 1 Overload",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_tentacle": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u89e6\u89d2",
            "en": "Magic Tentacle"
        },
        "cost_e": 0,
        "cost_m": 2,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u81ea\u5df1\u56de\u5408\u5f00\u59cb\u65f6\uff0c\u62bd1\u5f20\u724c",
        "base_text_en": "At the start of your turn, draw 1",
        "upgrade_text": "\u81ea\u5df1\u56de\u5408\u5f00\u59cb\u65f6\uff0c\u62bd1\u5f20\u724c",
        "upgrade_text_en": "At the start of your turn, draw 1",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_seed": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u79cd\u5b50",
            "en": "Magic Seed"
        },
        "cost_e": 1,
        "cost_m": 2,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u672c\u724c\u83b7\u5f97\u9b54\u529b\u8fc5\u63771\uff1b\u56de\u590d\u81ea\u5df14M",
        "base_text_en": "This card gains Magic Swift 1; recover 4 M",
        "upgrade_text": "\u672c\u724c\u83b7\u5f97\u9b54\u529b\u8fc5\u63771\uff1b\u56de\u590d\u81ea\u5df15M",
        "upgrade_text_en": "This card gains Magic Swift 1; recover 5 M",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_tomato": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u756a\u8304",
            "en": "Magic Tomato"
        },
        "cost_e": 2,
        "cost_m": 0,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "",
        "base_text": "\u5bf9\u76ee\u6807\u9020\u6210\uff0813+\u672c\u573a\u6218\u6597\u5df2\u6d88\u8017\u7684M\uff09D",
        "base_text_en": "Deal (13 + M spent this combat) D to the target",
        "upgrade_text": "\u5bf9\u76ee\u6807\u9020\u6210\uff0818+\u672c\u573a\u6218\u6597\u5df2\u6d88\u8017\u7684M\uff09D",
        "upgrade_text_en": "Deal (18 + M spent this combat) D to the target",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_stick": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u6728\u68cd",
            "en": "Magic Stick"
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u56de\u590d\uff082+\u5f53\u524d\u5b58\u6d3b\u654c\u4eba\u6570\u91cf\uff09M",
        "base_text_en": "Recover (2 + number of living enemies) M",
        "upgrade_text": "\u56de\u590d\uff083+\u5f53\u524d\u5b58\u6d3b\u654c\u4eba\u6570\u91cf\uff09M",
        "upgrade_text_en": "Recover (3 + number of living enemies) M",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_palm_leaf": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u68d5\u6988\u53f6",
            "en": "Magic Palm Leaf"
        },
        "cost_e": 2,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u81ea\u5df1\u83b7\u5f9710S\uff1b\u56de\u590d3M",
        "base_text_en": "Gain 10 S; recover 3 M",
        "upgrade_text": "\u81ea\u5df1\u83b7\u5f9714S\uff1b\u56de\u590d3M",
        "upgrade_text_en": "Gain 14 S; recover 3 M",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_iodine": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u7898",
            "en": "Magic Iodine"
        },
        "cost_e": 1,
        "cost_m": 3,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u81ea\u5df1\u56de\u5408\u7ed3\u675f\u65f6\uff0c\u5bf9\u6240\u6709\u654c\u4eba\u9020\u62107\u7535\u51fb\u4f24\u5bb3",
        "base_text_en": "At the end of your turn, deal 7 electric damage to all enemies",
        "upgrade_text": "\u81ea\u5df1\u56de\u5408\u7ed3\u675f\u65f6\uff0c\u5bf9\u6240\u6709\u654c\u4eba\u9020\u62107\u7535\u51fb\u4f24\u5bb3",
        "upgrade_text_en": "At the end of your turn, deal 7 electric damage to all enemies",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_basil": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u7f57\u52d2",
            "en": "Magic Basil"
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u82e5\u81ea\u5df1\u6ca1\u6709M\uff0c\u56de\u590d4M\uff1b\u5426\u5219\u56de\u590d2M",
        "base_text_en": "If you have no M, recover 4 M; otherwise recover 2 M",
        "upgrade_text": "\u82e5\u81ea\u5df1\u6ca1\u6709M\uff0c\u56de\u590d6M\uff1b\u5426\u5219\u56de\u590d2M",
        "upgrade_text_en": "If you have no M, recover 6 M; otherwise recover 2 M",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_balsam": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u9999\u8102",
            "en": "Magic Balsam"
        },
        "cost_e": 0,
        "cost_m": 2,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u968f\u673a\u5c063\u5f20\u5e26\u6709M\u6d88\u8017\u7684\u724c\u52a0\u5165\u624b\u724c\uff1b\u5b83\u4eec\u83b7\u5f97\u865a\u65e0\u4e0e\u653e\u9010",
        "base_text_en": "Add 3 random cards with M costs to your hand; they gain Void and Exile",
        "upgrade_text": "\u968f\u673a\u5c063\u5f20\u5e26\u6709M\u6d88\u8017\u7684\u5347\u7ea7\u724c\u52a0\u5165\u624b\u724c\uff1b\u5b83\u4eec\u83b7\u5f97\u865a\u65e0\u4e0e\u653e\u9010",
        "upgrade_text_en": "Add 3 random upgraded cards with M costs to your hand; they gain Void and Exile",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_bubble_bomb": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u6ce1\u6ce1\u70b8\u5f39",
            "en": "Magic Bubble Bomb"
        },
        "cost_e": 1,
        "cost_m": 3,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "\u5e7f\u57df\u6253\u51fb",
        "base_text": "\u5bf9\u76ee\u6807\u9020\u621014D\uff0c\u5e76\u65bd\u52a02\u5c42\u865a\u5f31",
        "base_text_en": "Deal 14 D to the target and apply 2 Weak",
        "upgrade_text": "\u5bf9\u76ee\u6807\u9020\u621017D\uff0c\u5e76\u65bd\u52a03\u5c42\u865a\u5f31",
        "upgrade_text_en": "Deal 17 D to the target and apply 3 Weak",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_lightning": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u95ea\u7535",
            "en": "Magic Lightning"
        },
        "cost_e": 0,
        "cost_m": 4,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "\u5e7f\u57df\u6253\u51fb",
        "base_text": "\u5bf9\u76ee\u6807\u9020\u62107\u70b9\u7535\u51fb\u4f24\u5bb32\u6b21",
        "base_text_en": "Deal 7 electric damage to the target 2 times",
        "upgrade_text": "\u5bf9\u76ee\u6807\u9020\u621010\u70b9\u7535\u51fb\u4f24\u5bb32\u6b21",
        "upgrade_text_en": "Deal 10 electric damage to the target 2 times",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_shovel": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u94f2\u5b50",
            "en": "Magic Shovel"
        },
        "cost_e": 0,
        "cost_m": 8,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "\u653e\u9010\uff0c\u865a\u65e0",
        "base_text": "\u81ea\u5df1\u83b7\u5f971\u5c42\u9690\u5f62",
        "base_text_en": "Gain 1 Invisible",
        "upgrade_text": "\u79fb\u9664\u865a\u65e0\uff1b\u81ea\u5df1\u83b7\u5f971\u5c42\u9690\u5f62",
        "upgrade_text_en": "Remove Void; gain 1 Invisible",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_sponge": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u6d77\u7ef5",
            "en": "Magic Sponge"
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u56de\u590d\u81ea\u5df18M\uff1b\u81ea\u5df1\u83b7\u5f9712\u5c42\u9b54\u529b\u8d85\u8f7d",
        "base_text_en": "Recover 8 M; gain 12 Magic Overload",
        "upgrade_text": "\u56de\u590d\u81ea\u5df18M\uff1b\u81ea\u5df1\u83b7\u5f9712\u5c42\u9b54\u529b\u8d85\u8f7d",
        "upgrade_text_en": "Recover 8 M; gain 12 Magic Overload",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_pearl": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u73cd\u73e0",
            "en": "Magic Pearl"
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "\u653e\u9010",
        "base_text": "\u5bf9\u76ee\u6807\u9020\u62107D\uff1b\u6d88\u8017\u81f3\u591a10M\uff0c\u6bcf\u6d88\u80171M\u62bd1\u5f20\u724c",
        "base_text_en": "Deal 7 D to the target; spend up to 10 M, drawing 1 per M spent",
        "upgrade_text": "\u79fb\u9664\u653e\u9010\uff1b\u5bf9\u76ee\u6807\u9020\u621010D\uff1b\u6d88\u8017\u81f3\u591a10M\uff0c\u6bcf\u6d88\u80171M\u62bd1\u5f20\u724c",
        "upgrade_text_en": "Remove Exile; deal 10 D to the target; spend up to 10 M, drawing 1 per M spent",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_rock": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u77f3\u5934",
            "en": "Magic Rock"
        },
        "cost_e": 0,
        "cost_m": 3,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "",
        "base_text": "\u5bf9\u76ee\u6807\u9020\u62107D\uff0c\u5e76\u65bd\u52a02\u5c42\u6613\u4f24",
        "base_text_en": "Deal 7 D to the target and apply 2 Vulnerable",
        "upgrade_text": "\u5bf9\u76ee\u6807\u9020\u62109D\uff0c\u5e76\u65bd\u52a03\u5c42\u6613\u4f24",
        "upgrade_text_en": "Deal 9 D to the target and apply 3 Vulnerable",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_blueberry": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u84dd\u8393",
            "en": "Magic Blueberry"
        },
        "cost_e": 2,
        "cost_m": 3,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u81ea\u5df1\u6253\u51fa\u5e26\u6709M\u6d88\u8017\u7684\u724c\u65f6\uff0c\u5bf9\u968f\u673a\u654c\u4eba\u9020\u62105\u7535\u51fb\u4f24\u5bb3",
        "base_text_en": "When you play a card with an M cost, deal 5 electric damage to a random enemy",
        "upgrade_text": "\u81ea\u5df1\u6253\u51fa\u5e26\u6709M\u6d88\u8017\u7684\u724c\u65f6\uff0c\u5bf9\u968f\u673a\u654c\u4eba\u9020\u62105\u7535\u51fb\u4f24\u5bb3",
        "upgrade_text_en": "When you play a card with an M cost, deal 5 electric damage to a random enemy",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_battery_delayed": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u7535\u6c60",
            "en": "Magic Battery"
        },
        "cost_e": 1,
        "cost_m": 3,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u81ea\u5df1\u56de\u5408\u7ed3\u675f\u65f6\u82e5\u4ecd\u6709M\uff0c\u4e0b\u56de\u5408\u5f00\u59cb\u65f6\u56de\u590d2M",
        "base_text_en": "At the end of your turn, if you have any M left, recover 2 M at the start of the next turn",
        "upgrade_text": "\u81ea\u5df1\u56de\u5408\u7ed3\u675f\u65f6\u82e5\u4ecd\u6709M\uff0c\u4e0b\u56de\u5408\u5f00\u59cb\u65f6\u56de\u590d2M",
        "upgrade_text_en": "At the end of your turn, if you have any M left, recover 2 M at the start of the next turn",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_serration": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u952f\u9f7f",
            "en": "Magic Serration"
        },
        "cost_e": 0,
        "cost_m": 5,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u672c\u56de\u5408\u81ea\u5df1\u9020\u6210\u7684\u4f24\u5bb3\u7ffb\u500d",
        "base_text_en": "Double the damage you deal this turn",
        "upgrade_text": "\u672c\u56de\u5408\u81ea\u5df1\u9020\u6210\u7684\u4f24\u5bb3\u7ffb\u500d",
        "upgrade_text_en": "Double the damage you deal this turn",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_starfish": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u6d77\u661f",
            "en": "Magic Starfish"
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u4ec5\u5f53\u81ea\u5df1\u4e0a\u56de\u5408\u672a\u53d7\u4f24\u65f6\u624d\u80fd\u6253\u51fa\uff1b\u81ea\u5df1\u83b7\u5f977S\uff1b\u56de\u590d2M",
        "base_text_en": "Playable only if you took no damage last turn; gain 7 S; recover 2 M",
        "upgrade_text": "\u4ec5\u5f53\u81ea\u5df1\u4e0a\u56de\u5408\u672a\u53d7\u4f24\u65f6\u624d\u80fd\u6253\u51fa\uff1b\u81ea\u5df1\u83b7\u5f9710S\uff1b\u56de\u590d2M",
        "upgrade_text_en": "Playable only if you took no damage last turn; gain 10 S; recover 2 M",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_honey_shield": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u8702\u871c",
            "en": "Magic Honey"
        },
        "cost_e": 1,
        "cost_m": 1,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u81ea\u5df1\u83b7\u5f97\uff0812+\u5f53\u524dM\uff09S",
        "base_text_en": "Gain (12 + current M) S",
        "upgrade_text": "\u81ea\u5df1\u83b7\u5f97\uff0816+\u5f53\u524dM\uff09S",
        "upgrade_text_en": "Gain (16 + current M) S",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_constellation": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u661f\u5ea7",
            "en": "Magic Constellation"
        },
        "cost_e": 2,
        "cost_m": 2,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "",
        "base_text": "\u5bf9\u76ee\u6807\u9020\u621034D\uff1b\u672c\u56de\u5408\u4f60\u6240\u6709\u624b\u724c\u7684M\u82b1\u8d39+1",
        "base_text_en": "Deal 34 D to the target; your hand cards cost 1 more M this turn",
        "upgrade_text": "\u5bf9\u76ee\u6807\u9020\u621042D\uff1b\u672c\u56de\u5408\u4f60\u6240\u6709\u624b\u724c\u7684M\u82b1\u8d39+1",
        "upgrade_text_en": "Deal 42 D to the target; your hand cards cost 1 more M this turn",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_mask": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u53e3\u7f69",
            "en": "Magic Mask"
        },
        "cost_e": 0,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "\u653e\u9010",
        "base_text": "\u672c\u56de\u5408\u5185\uff0c\u6bcf\u6d88\u80171M\uff0c\u81ea\u5df1\u83b7\u5f973S",
        "base_text_en": "This turn, gain 3 S for each M you spend",
        "upgrade_text": "\u79fb\u9664\u653e\u9010\uff1b\u672c\u56de\u5408\u5185\uff0c\u6bcf\u6d88\u80171M\uff0c\u81ea\u5df1\u83b7\u5f973S",
        "upgrade_text_en": "Remove Exile; this turn, gain 3 S for each M you spend",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_missile": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u5bfc\u5f39",
            "en": "Magic Missile"
        },
        "cost_e": 1,
        "cost_m": 3,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "\u84c4\u52bf\u5f85\u53d1",
        "base_text": "\u5bf9\u76ee\u6807\u9020\u621015D\uff1b\u62bd3\u5f20\u724c",
        "base_text_en": "Deal 15 D to the target; draw 3",
        "upgrade_text": "\u5bf9\u76ee\u6807\u9020\u621017D\uff1b\u62bd4\u5f20\u724c",
        "upgrade_text_en": "Deal 17 D to the target; draw 4",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_wind": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u98ce",
            "en": "Magic Wind"
        },
        "cost_e": 0,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u5f03\u7f6e\u6240\u6709\u65e0M\u6d88\u8017\u7684\u624b\u724c\uff0c\u7136\u540e\u62bd\u7b49\u91cf\u5e26\u6709M\u6d88\u8017\u7684\u724c",
        "base_text_en": "Discard all hand cards without M costs, then draw that many cards with M costs",
        "upgrade_text": "\u5f03\u7f6e\u6240\u6709\u65e0M\u6d88\u8017\u7684\u624b\u724c\uff0c\u7136\u540e\u62bd\u7b49\u91cf+1\u5f20\u5e26\u6709M\u6d88\u8017\u7684\u724c",
        "upgrade_text_en": "Discard all hand cards without M costs, then draw that many plus 1 cards with M costs",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_chromosome": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u67d3\u8272\u4f53",
            "en": "Magic Chromosome"
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u81ea\u5df1\u6bcf\u56de\u590d1M\uff0c\u83b7\u5f972S",
        "base_text_en": "Whenever you recover M, gain 2 S per M recovered",
        "upgrade_text": "\u81ea\u5df1\u6bcf\u56de\u590d1M\uff0c\u83b7\u5f973S",
        "upgrade_text_en": "Whenever you recover M, gain 3 S per M recovered",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_rose": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u73ab\u7470",
            "en": "Magic Rose"
        },
        "cost_e": 0,
        "cost_m": 2,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u81ea\u5df1\u83b7\u5f979S",
        "base_text_en": "Gain 9 S",
        "upgrade_text": "\u81ea\u5df1\u83b7\u5f9712S",
        "upgrade_text_en": "Gain 12 S",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_beeswax": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u8702\u8721",
            "en": "Magic Beeswax"
        },
        "cost_e": 1,
        "cost_m": 2,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u672c\u56de\u5408\u81ea\u5df1\u7684\u62a4\u76fe\u53d7\u5230\u7684\u4f24\u5bb3\u51cf\u534a\uff1b\u81ea\u5df1\u83b7\u5f975S",
        "base_text_en": "Halve damage taken by your Shield this turn; gain 5 S",
        "upgrade_text": "\u672c\u56de\u5408\u81ea\u5df1\u7684\u62a4\u76fe\u53d7\u5230\u7684\u4f24\u5bb3\u51cf\u534a\uff1b\u81ea\u5df1\u83b7\u5f978S",
        "upgrade_text_en": "Halve damage taken by your Shield this turn; gain 8 S",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_balloon": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u6c14\u7403",
            "en": "Magic Balloon"
        },
        "cost_e": 0,
        "cost_m": 2,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u62bd3\u5f20\u724c\uff0c\u7136\u540e\u9009\u62e92\u5f20\u624b\u724c\u7f6e\u4e8e\u62bd\u724c\u5806\u9876",
        "base_text_en": "Draw 3, then choose 2 hand cards and put them on top of the draw pile",
        "upgrade_text": "\u62bd4\u5f20\u724c\uff0c\u7136\u540e\u9009\u62e92\u5f20\u624b\u724c\u7f6e\u4e8e\u62bd\u724c\u5806\u9876",
        "upgrade_text_en": "Draw 4, then choose 2 hand cards and put them on top of the draw pile",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_air": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u7a7a\u6c14",
            "en": "Magic Air"
        },
        "cost_e": 0,
        "cost_m": 3,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u5c06\u81ea\u8eab\u7684\u62a4\u76fe\u7ffb\u500d",
        "base_text_en": "Double your Shield",
        "upgrade_text": "\u5c06\u81ea\u8eab\u7684\u62a4\u76fe\u7ffb3\u500d",
        "upgrade_text_en": "Triple your Shield",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_rmb": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u4eba\u6c11\u5e01",
            "en": "Magic RMB"
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u4e0b\u4e00\u573a\u6218\u6597\u5f00\u59cb\u65f6\uff0c\u83b7\u5f972M",
        "base_text_en": "At the start of the next combat, gain 2 M",
        "upgrade_text": "\u4e0b\u4e00\u573a\u6218\u6597\u5f00\u59cb\u65f6\uff0c\u83b7\u5f972M",
        "upgrade_text_en": "At the start of the next combat, gain 2 M",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "capacitor": {
        "character_id": "mage",
        "name": {
            "zh": "\u7535\u5bb9\u5668",
            "en": "Capacitor"
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u5f53\u4f60\u901a\u8fc7\u7535\u51fb\u4f24\u5bb3\u5bf9\u654c\u4eba\u65bd\u52a0\u9759\u7535\u65f6\uff0c\u65bd\u52a0\u91cf\u589e\u52a050%",
        "base_text_en": "When you apply Static through electric damage, increase the amount applied by 50%",
        "upgrade_text": "\u5f53\u4f60\u901a\u8fc7\u7535\u51fb\u4f24\u5bb3\u5bf9\u654c\u4eba\u65bd\u52a0\u9759\u7535\u65f6\uff0c\u65bd\u52a0\u91cf\u589e\u52a075%",
        "upgrade_text_en": "When you apply Static through electric damage, increase the amount applied by 75%",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "battery": {
        "character_id": "mage",
        "name": {
            "zh": "\u7535\u6c60",
            "en": "Battery"
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u81ea\u5df1\u53d7\u5230\u653b\u51fb\u65f6\uff0c\u5bf9\u653b\u51fb\u8005\u65bd\u52a04\u5c42\u9759\u7535",
        "base_text_en": "When you are attacked, apply 4 Static to the attacker",
        "upgrade_text": "\u81ea\u5df1\u53d7\u5230\u653b\u51fb\u65f6\uff0c\u5bf9\u653b\u51fb\u8005\u65bd\u52a06\u5c42\u9759\u7535",
        "upgrade_text_en": "When you are attacked, apply 6 Static to the attacker",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "plasma": {
        "character_id": "mage",
        "name": {
            "zh": "\u7b49\u79bb\u5b50\u4f53",
            "en": "Plasma"
        },
        "cost_e": 3,
        "cost_m": 0,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "",
        "base_text": "\u5bf9\u76ee\u6807\u9020\u62106\u70b9\u7535\u51fb\u4f24\u5bb35\u6b21",
        "base_text_en": "Deal 6 electric damage to the target 5 times",
        "upgrade_text": "\u5bf9\u76ee\u6807\u9020\u62108\u70b9\u7535\u51fb\u4f24\u5bb35\u6b21",
        "upgrade_text_en": "Deal 8 electric damage to the target 5 times",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "ruby": {
        "character_id": "mage",
        "name": {
            "zh": "\u7ea2\u5b9d\u77f3",
            "en": "Ruby"
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u6bcf\u5f53\u654c\u4eba\u89e6\u53d1\u9759\u7535\u65f6\uff0c\u5bf9\u5176\u9020\u62108D",
        "base_text_en": "Whenever an enemy triggers Static, deal 8 D to it",
        "upgrade_text": "\u6bcf\u5f53\u654c\u4eba\u89e6\u53d1\u9759\u7535\u65f6\uff0c\u5bf9\u5176\u9020\u621011D",
        "upgrade_text_en": "Whenever an enemy triggers Static, deal 11 D to it",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_ruby": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u7ea2\u5b9d\u77f3",
            "en": "Magic Ruby"
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u6bcf\u5f53\u654c\u4eba\u89e6\u53d1\u9759\u7535\u65f6\uff0c\u81ea\u5df1\u83b7\u5f973S",
        "base_text_en": "Whenever an enemy triggers Static, gain 3 S",
        "upgrade_text": "\u6bcf\u5f53\u654c\u4eba\u89e6\u53d1\u9759\u7535\u65f6\uff0c\u81ea\u5df1\u83b7\u5f974S",
        "upgrade_text_en": "Whenever an enemy triggers Static, gain 4 S",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_capacitor": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u7535\u5bb9\u5668",
            "en": "Magic Capacitor"
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u6bcf\u5f53\u654c\u4eba\u89e6\u53d1\u9759\u7535\u65f6\uff0c\u81ea\u5df1\u83b7\u5f971M",
        "base_text_en": "Whenever an enemy triggers Static, gain 1 M",
        "upgrade_text": "\u6bcf\u5f53\u654c\u4eba\u89e6\u53d1\u9759\u7535\u65f6\uff0c\u81ea\u5df1\u83b7\u5f971M",
        "upgrade_text_en": "Whenever an enemy triggers Static, gain 1 M",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "copper_rod": {
        "character_id": "mage",
        "name": {
            "zh": "\u94dc\u68d2",
            "en": "Copper Rod"
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u81ea\u5df1\u83b7\u5f978S\uff1b\u5bf9\u76ee\u6807\u65bd\u52a03\u5c42\u9759\u7535",
        "base_text_en": "Gain 8 S; apply 3 Static to the target",
        "upgrade_text": "\u81ea\u5df1\u83b7\u5f9710S\uff1b\u5bf9\u76ee\u6807\u65bd\u52a06\u5c42\u9759\u7535",
        "upgrade_text_en": "Gain 10 S; apply 6 Static to the target",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_copper_rod": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u94dc\u68d2",
            "en": "Magic Copper Rod"
        },
        "cost_e": 0,
        "cost_m": 2,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u5c06\u76ee\u6807\u7684\u9759\u7535\u7ffb\u500d",
        "base_text_en": "Double the target's Static",
        "upgrade_text": "\u5c06\u76ee\u6807\u7684\u9759\u7535\u7ffb3\u500d",
        "upgrade_text_en": "Triple the target's Static",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_lithium": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u9502",
            "en": "Magic Lithium"
        },
        "cost_e": 2,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u6bcf\u5f53\u654c\u4eba\u89e6\u53d1\u9759\u7535\u65f6\uff0c\u62bd1\u5f20\u724c",
        "base_text_en": "Whenever an enemy triggers Static, draw 1",
        "upgrade_text": "\u6bcf\u5f53\u654c\u4eba\u89e6\u53d1\u9759\u7535\u65f6\uff0c\u62bd1\u5f20\u724c",
        "upgrade_text_en": "Whenever an enemy triggers Static, draw 1",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "electronic_missile": {
        "character_id": "mage",
        "name": {
            "zh": "\u7535\u5b50\u5bfc\u5f39",
            "en": "Electronic Missile"
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "\u84c4\u52bf\u5f85\u53d1",
        "base_text": "\u5bf9\u76ee\u6807\u9020\u62109\u70b9\u7535\u51fb\u4f24\u5bb3\uff1b\u62bd2\u5f20\u724c",
        "base_text_en": "Deal 9 electric damage to the target; draw 2",
        "upgrade_text": "\u5bf9\u76ee\u6807\u9020\u621011\u70b9\u7535\u51fb\u4f24\u5bb3\uff1b\u62bd3\u5f20\u724c",
        "upgrade_text_en": "Deal 11 electric damage to the target; draw 3",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_electronic_missile": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u7535\u5b50\u5bfc\u5f39",
            "en": "Magic Electronic Missile"
        },
        "cost_e": 0,
        "cost_m": 2,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "\u84c4\u52bf\u5f85\u53d1\uff0c\u56de\u8f6c",
        "base_text": "\u5bf9\u76ee\u6807\u9020\u62105\u70b9\u7535\u51fb\u4f24\u5bb3\uff1b\u62bd1\u5f20\u724c\uff1b\u5c06\u6b64\u724c\u7f6e\u4e8e\u62bd\u724c\u5806\u9876",
        "base_text_en": "Deal 5 electric damage to the target; draw 1; put this card on top of the draw pile",
        "upgrade_text": "\u5bf9\u76ee\u6807\u9020\u62107\u70b9\u7535\u51fb\u4f24\u5bb3\uff1b\u62bd1\u5f20\u724c\uff1b\u5c06\u6b64\u724c\u7f6e\u4e8e\u62bd\u724c\u5806\u9876",
        "upgrade_text_en": "Deal 7 electric damage to the target; draw 1; put this card on top of the draw pile",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "enchanted_magic_basic": {
        "character_id": "mage",
        "name": {"zh": "附魔魔法基本", "en": "Enchanted Magic Basic"},
        "cost_e": 0,
        "cost_m": 0,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "",
        "base_text": "回复2M；对目标造成13点电击伤害。",
        "base_text_en": "Recover 2 M; deal 13 Electric Damage to the target.",
        "upgrade_text": "回复3M；对目标造成18点电击伤害。",
        "upgrade_text_en": "Recover 3 M; deal 18 Electric Damage to the target.",
        "rarity": "super",
        "authored_rarity": "超级",
        "implementation_status": "authored"
    },
    "fractal_lightning": {
        "character_id": "mage",
        "name": {"zh": "分形闪电", "en": "Fractal Lightning"},
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "你造成电击伤害时，对目标施加3层静电。",
        "base_text_en": "Whenever you deal Electric Damage, apply 3 Static to the target.",
        "upgrade_text": "你造成电击伤害时，对目标施加4层静电。",
        "upgrade_text_en": "Whenever you deal Electric Damage, apply 4 Static to the target.",
        "rarity": "rare",
        "authored_rarity": "稀有",
        "implementation_status": "authored"
    },
    "magic_fractal_lightning": {
        "character_id": "mage",
        "name": {"zh": "魔法分形闪电", "en": "Magic Fractal Lightning"},
        "cost_e": 0,
        "cost_m": 2,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "选择1个目标：其静电本回合不会被触发；回合结束时，其静电层数翻倍并触发。",
        "base_text_en": "Choose a target. Its Static cannot trigger this round; at round end, double and trigger it.",
        "upgrade_text": "选择1个目标：其静电本回合不会被触发；回合结束时，其静电层数翻倍并触发。",
        "upgrade_text_en": "Choose a target. Its Static cannot trigger this round; at round end, double and trigger it.",
        "rarity": "ultra",
        "authored_rarity": "究级",
        "implementation_status": "authored"
    },
    "orb": {
        "character_id": "mage",
        "name": {"zh": "球", "en": "Orb"},
        "cost_e": 3,
        "cost_m": 0,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "",
        "base_text": "对目标造成33点电击伤害。",
        "base_text_en": "Deal 33 Electric Damage to the target.",
        "upgrade_text": "对目标造成40点电击伤害。",
        "upgrade_text_en": "Deal 40 Electric Damage to the target.",
        "rarity": "rare",
        "authored_rarity": "稀有",
        "implementation_status": "authored"
    },
    "magic_orb": {
        "character_id": "mage",
        "name": {"zh": "魔法球", "en": "Magic Orb"},
        "cost_e": 0,
        "cost_m": "X",
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "",
        "base_text": "消耗全部M；每消耗1M，对目标造成6点电击伤害。",
        "base_text_en": "Spend all M; deal 6 Electric Damage to the target for each M spent.",
        "upgrade_text": "消耗全部M；每消耗1M，对目标造成8点电击伤害。",
        "upgrade_text_en": "Spend all M; deal 8 Electric Damage to the target for each M spent.",
        "rarity": "ultra",
        "authored_rarity": "究级",
        "implementation_status": "authored"
    },
    "magic_elemental_force": {
        "character_id": "mage",
        "name": {"zh": "魔法元素之力", "en": "Magic Elemental Force"},
        "cost_e": 2,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "你每获得1M，获得1层暂时力量。",
        "base_text_en": "Whenever you gain 1 M, gain 1 Temporary Power.",
        "upgrade_text": "你每获得1M，获得1层暂时力量。",
        "upgrade_text_en": "Whenever you gain 1 M, gain 1 Temporary Power.",
        "rarity": "ultra",
        "authored_rarity": "究级",
        "implementation_status": "authored"
    },
    "usain_bolt": {
        "character_id": "mage",
        "name": {"zh": "尤塞恩·博尔特", "en": "Usain Bolt"},
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "你造成电击伤害时，触发目标静电一次。",
        "base_text_en": "Whenever you deal Electric Damage, trigger the target's Static once.",
        "upgrade_text": "你造成电击伤害时，触发目标静电一次。",
        "upgrade_text_en": "Whenever you deal Electric Damage, trigger the target's Static once.",
        "rarity": "rare",
        "authored_rarity": "稀有",
        "implementation_status": "authored"
    },
    "magic_usain_bolt": {
        "character_id": "mage",
        "name": {"zh": "魔法尤塞恩·博尔特", "en": "Magic Usain Bolt"},
        "cost_e": 0,
        "cost_m": 2,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "目标下一次触发静电时，不会减少其层数。",
        "base_text_en": "The target's next Static trigger does not consume its stacks.",
        "upgrade_text": "目标下2次触发静电时，不会减少其层数。",
        "upgrade_text_en": "The target's next 2 Static triggers do not consume its stacks.",
        "rarity": "ultra",
        "authored_rarity": "究级",
        "implementation_status": "authored"
    },
    "nether_lightning": {
        "character_id": "mage",
        "name": {"zh": "冥界闪电", "en": "Nether Lightning"},
        "cost_e": 2,
        "cost_m": 0,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "",
        "base_text": "随机对生物造成7点电击伤害，共3次。",
        "base_text_en": "Deal 7 Electric Damage to a random creature, 3 times.",
        "upgrade_text": "随机对生物造成9点电击伤害，共3次。",
        "upgrade_text_en": "Deal 9 Electric Damage to a random creature, 3 times.",
        "rarity": "common",
        "authored_rarity": "普通",
        "implementation_status": "authored"
    },
    "magic_nether_lightning": {
        "character_id": "mage",
        "name": {"zh": "魔法冥界闪电", "en": "Magic Nether Lightning"},
        "cost_e": 1,
        "cost_m": 2,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "你每获得1M，对随机生物施加3层静电。",
        "base_text_en": "Whenever you gain 1 M, apply 3 Static to a random creature.",
        "upgrade_text": "你每获得1M，对随机生物施加4层静电。",
        "upgrade_text_en": "Whenever you gain 1 M, apply 4 Static to a random creature.",
        "rarity": "ultra",
        "authored_rarity": "究级",
        "implementation_status": "authored"
    }
}


STORY_CHARACTER_TERMS = {
    "electric_damage": {
        "name": {
            "zh": "\u7535\u51fb\u4f24\u5bb3",
            "en": "Electric Damage"
        },
        "description": {
            "zh": "\u82e5\u76ee\u6807\u6ca1\u6709\u9759\u7535\u5219\u4e0d\u9020\u6210\u4f24\u5bb3\u6539\u4e3a\u65bd\u52a0\u7b49\u91cf\u9759\u7535\uff0c\u82e5\u6709\u5219\u89c6\u4e3a\u89e6\u53d1\u9759\u7535\uff0c\u6d88\u8017\u76ee\u6807\u6240\u6709\u9759\u7535\u9020\u6210\u672c\u6b21\u4f24\u5bb3+\u76ee\u6807\u9759\u7535\u5c42\u6570\u70b9\u4f24\u5bb3",
            "en": ""
        },
        "implementation_status": "authored"
    }
}


STORY_CHARACTER_RELIC_DESIGNS = {
    'magic_source': {
        'character_id': 'mage',
        'name': {'zh': '魔力源泉', 'en': ''},
        'effect_text': '回合开始时，回复1M',
        'acquisition': 'starter',
        'rarity': 'special',
        'implementation_status': 'authored',
    },
}
