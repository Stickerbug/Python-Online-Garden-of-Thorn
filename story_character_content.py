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
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 2,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "",
        "base_text": "\u9020\u621013D",
        "upgrade_text": "\u9020\u621018D",
        "rarity": "starter",
        "authored_rarity": "\u57fa\u7840",
        "implementation_status": "authored"
    },
    "mage_orange": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u6a59\u5b50",
            "en": ""
        },
        "cost_e": 0,
        "cost_m": 1,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "\u56de\u8f6c",
        "base_text": "\u9020\u62105D",
        "upgrade_text": "\u9020\u62107D",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_coral": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u73ca\u745a",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 2,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "\u653e\u9010",
        "base_text": "17D\uff0c\u5c062\u5f20\u5177\u6709\u9b54\u529b\u8fc5\u63771\uff0c\u865a\u65e0\u7684\u9b54\u6cd5\u73ca\u745a\u7f6e\u4e8e\u62bd\u724c\u5806\u9876",
        "upgrade_text": "22D\uff0c\u5c062\u5f20\u5177\u6709\u9b54\u529b\u8fc5\u63771\u7684\u9b54\u6cd5\u73ca\u745a+\u7f6e\u4e8e\u62bd\u724c\u5806\u9876",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_leaf": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u53f6",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u83b7\u5f97\u4e00\u5c42\u9b54\u529b\u518d\u751f:\u6bcf\u56de\u5408\u5f00\u59cb\u65f6\u56de\u590dX\u9b54\u529b",
        "upgrade_text": "\u82b1\u8d39-1E",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_compass": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u6307\u5357\u9488",
            "en": ""
        },
        "cost_e": 0,
        "cost_m": 1,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "\u653e\u9010",
        "base_text": "\u5c06\u62bd\u724c\u5806\u6216\u5f03\u724c\u5806\u4e2d\u7684\u4e00\u5f20\u724c\u52a0\u5165\u624b\u4e2d",
        "upgrade_text": "\u56fa\u6709\uff0c\u5c06\u62bd\u724c\u5806\u6216\u5f03\u724c\u5806\u4e2d\u7684\u4e00\u5f20\u724c\u52a0\u5165\u624b\u4e2d",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_fries": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u85af\u6761",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 2,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "\u653e\u9010",
        "base_text": "\u56de\u590d7H",
        "upgrade_text": "\u56de\u590d10H",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_coffee": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u5496\u5561",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "\u653e\u9010",
        "base_text": "\u56de\u590d4M",
        "upgrade_text": "\u56de\u590d5M",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_blood_blade": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u8840\u5203",
            "en": ""
        },
        "cost_e": 0,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "\u56de\u8f6c",
        "base_text": "\u56de\u590d2M\u83b7\u5f971\u7834\u635f",
        "upgrade_text": "\u56de\u590d3M\u83b7\u5f971\u7834\u635f",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_cotton": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u68c9\u82b1",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 1,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u5c06\u81ea\u8eab\u7684\u9b54\u6cd5\u62a4\u76fe\u8bbe\u4e3a4",
        "upgrade_text": "\u56fa\u6709\uff0c\u5c06\u81ea\u8eab\u7684\u9b54\u6cd5\u62a4\u76fe\u8bbe\u4e3a4",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_sunflower": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u5411\u65e5\u8475",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 1,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u6bcf\u4f7f\u75282\u80fd\u91cf\uff0c\u56de\u590d1M",
        "upgrade_text": "\u82b1\u8d39-1\uff0c\u6bcf\u4f7f\u75282\u80fd\u91cf\uff0c\u56de\u590d1M",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_quantum": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u91cf\u5b50",
            "en": ""
        },
        "cost_e": 2,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "\u865a\u65e0\uff0c\u653e\u9010",
        "base_text": "\u672c\u56de\u5408\u4f60\u6240\u6709\u5361\u724c\u7684M\u82b1\u8d39\u4e0e\u80fd\u91cf\u82b1\u8d39\u5bf9\u8c03",
        "upgrade_text": "\u53bb\u9664\u865a\u65e0\uff0c\u672c\u56de\u5408\u4f60\u6240\u6709\u5361\u724c\u7684M\u82b1\u8d39\u4e0e\u80fd\u91cf\u82b1\u8d39\u5bf9\u8c03",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_wing": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u7fc5\u8180",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 2,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "",
        "base_text": "\u9020\u62109D\uff0c\u6d88\u8017\u81ea\u8eab\u81f3\u591a4m\uff0c\u6bcf\u989d\u5916\u6d88\u80171m\u5219\u989d\u5916\u653b\u51fb\u4e00\u6b21\u3002",
        "upgrade_text": "\u9020\u621012D\uff0c\u6d88\u8017\u81ea\u8eab\u81f3\u591a4m\uff0c\u6bcf\u989d\u5916\u6d88\u80171m\u989d\u5916\u653b\u51fb\u4e00\u6b21\u3002",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_bone": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u9aa8\u5934",
            "en": ""
        },
        "cost_e": 0,
        "cost_m": 3,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "",
        "base_text": "\u9020\u62109D\u83b7\u5f976S",
        "upgrade_text": "\u9020\u621012D\u83b7\u5f978S",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_dahlia": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u5927\u4e3d\u82b1",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u56de\u590d1M\uff0c\u83b7\u5f973\u5c421\u7ea7\u9b54\u529b\u56de\u590d",
        "upgrade_text": "\u56de\u590d1M\uff0c\u83b7\u5f974\u5c421\u7ea7\u9b54\u529b\u56de\u590d",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_soil": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u571f",
            "en": ""
        },
        "cost_e": 0,
        "cost_m": 4,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "\u653e\u9010",
        "base_text": "\u83b7\u5f9732S\uff0c\u83b7\u5f97\u8d85\u8f7d1",
        "upgrade_text": "\u83b7\u5f9740S\u8d85\u8f7d1",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_tentacle": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u89e6\u89d2",
            "en": ""
        },
        "cost_e": 0,
        "cost_m": 2,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u6bcf\u56de\u5408\u5f00\u59cb\u65f6\uff0c\u989d\u5916\u62bd\u4e00\u5f20\u724c",
        "upgrade_text": "\u83b7\u5f97\u56fa\u6709\uff0c\u6bcf\u56de\u5408\u5f00\u59cb\u65f6\uff0c\u989d\u5916\u62bd\u4e00\u5f20\u724c",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_seed": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u79cd\u5b50",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 2,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u4f7f\u7528\u65f6\uff0c\u83b7\u5f97\u9b54\u529b\u8fc5\u63771\uff0c\u56de\u590d4M",
        "upgrade_text": "\u4f7f\u7528\u65f6\uff0c\u83b7\u5f97\u9b54\u529b\u8fc5\u63771\uff0c\u56de\u590d5M",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_tomato": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u756a\u8304",
            "en": ""
        },
        "cost_e": 2,
        "cost_m": 0,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "",
        "base_text": "\u9020\u6210\uff0813+\u672c\u573a\u6218\u6597\u4e2d\u6d88\u8017\u9b54\u529b\u603b\u6570\uff09D",
        "upgrade_text": "\u9020\u6210\uff0818+\u672c\u573a\u6218\u6597\u4e2d\u6d88\u8017\u9b54\u529b\u603b\u6570\uff09D",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_stick": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u6728\u68cd",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u56de\u590d\uff082+\u654c\u4eba\u6570\u91cf\uff09M",
        "upgrade_text": "\u56de\u590d\uff083+\u654c\u4eba\u6570\u91cf\uff09M",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_palm_leaf": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u68d5\u6988\u53f6",
            "en": ""
        },
        "cost_e": 2,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u83b7\u5f9710S\uff0c\u56de\u590d3M",
        "upgrade_text": "\u83b7\u5f9714S\uff0c\u56de\u590d3M",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_iodine": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u7898",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 3,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u56de\u5408\u7ed3\u675f\u65f6\u5bf9\u6240\u6709\u654c\u4eba\u9020\u62107\u7535\u51fb\u4f24\u5bb3",
        "upgrade_text": "\u82b1\u8d39-1\uff0c\u56de\u5408\u7ed3\u675f\u65f6\u5bf9\u6240\u6709\u654c\u4eba\u9020\u62107\u7535\u51fb\u4f24\u5bb3",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_basil": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u7f57\u52d2",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u82e5\u6ca1\u6709M\u5219\u56de\u590d4M\uff0c\u5426\u5219\u56de\u590d2M",
        "upgrade_text": "\u82e5\u6ca1\u6709M\u5219\u56de\u590d6M\uff0c\u5426\u5219\u56de\u590d2M",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_balsam": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u9999\u8102",
            "en": ""
        },
        "cost_e": 0,
        "cost_m": 2,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u5c063\u5f20\u968f\u673a\u5e26\u6709M\u6d88\u8017\u7684\u724c\u52a0\u5165\u4f60\u7684\u624b\u724c\uff0c\u4f7f\u5b83\u4eec\u83b7\u5f97\u865a\u65e0\uff0c\u653e\u9010",
        "upgrade_text": "\u5c063\u5f20\u968f\u673a\u5e26\u6709M\u6d88\u8017\u5347\u7ea7\u8fc7\u7684\u724c\u52a0\u5165\u4f60\u7684\u624b\u724c\uff0c\u4f7f\u5b83\u4eec\u83b7\u5f97\u865a\u65e0\uff0c\u653e\u9010",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_bubble_bomb": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u6ce1\u6ce1\u70b8\u5f39",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 3,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "\u5e7f\u57df\u6253\u51fb",
        "base_text": "\u9020\u621014D\uff0c\u65bd\u52a02\u865a\u5f31",
        "upgrade_text": "\u9020\u621017D\uff0c\u65bd\u52a03\u865a\u5f31",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_lightning": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u95ea\u7535",
            "en": ""
        },
        "cost_e": 0,
        "cost_m": 4,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "\u5e7f\u57df\u6253\u51fb",
        "base_text": "\u9020\u62107\u70b9\u7535\u51fb\u4f24\u5bb32\u6b21",
        "upgrade_text": "\u9020\u621010\u70b9\u7535\u51fb\u4f24\u5bb32\u6b21",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_shovel": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u94f2\u5b50",
            "en": ""
        },
        "cost_e": 0,
        "cost_m": 8,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "\u653e\u9010\uff0c\u865a\u65e0",
        "base_text": "\u83b7\u5f97\u4e00\u56de\u5408\u9690\u5f62",
        "upgrade_text": "\u53d6\u6d88\u865a\u65e0\uff0c\u83b7\u5f97\u4e00\u56de\u5408\u9690\u5f62",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_sponge": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u6d77\u7ef5",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u56de\u590d8M\uff0c\u83b7\u5f9712\u9b54\u529b\u8d85\u8f7d",
        "upgrade_text": "\u589e\u52a0\u4fdd\u7559\uff0c\u56de\u590d8M\uff0c\u83b7\u5f9712\u9b54\u529b\u8d85\u8f7d",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_pearl": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u73cd\u73e0",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "\u653e\u9010",
        "base_text": "\u9020\u62107D\uff0c\u6d88\u8017\u81f3\u591a10\u70b9M\uff0c\u6bcf\u6d88\u8017\u4e00\u70b9\u62bd\u4e00\u5f20\u724c",
        "upgrade_text": "\u79fb\u9664\u653e\u9010\uff0c\u9020\u621010D\uff0c\u6d88\u8017\u81f3\u591a10\u70b9M\uff0c\u6bcf\u6d88\u8017\u4e00\u70b9\u62bd\u4e00\u5f20\u724c",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_rock": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u77f3\u5934",
            "en": ""
        },
        "cost_e": 0,
        "cost_m": 3,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "",
        "base_text": "7D 2\u6613\u4f24",
        "upgrade_text": "9D3\u6613\u4f24",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_blueberry": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u84dd\u8393",
            "en": ""
        },
        "cost_e": 2,
        "cost_m": 3,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u4f7f\u7528\u5e26\u6709M\u6d88\u8017\u7684\u724c\u65f6\uff0c\u5bf9\u968f\u673a\u654c\u4eba\u9020\u62105\u7535\u51fb\u4f24\u5bb3",
        "upgrade_text": "\u82b1\u8d39-1\uff0c\u4f7f\u7528\u5e26\u6709M\u6d88\u8017\u7684\u724c\u65f6\uff0c\u5bf9\u968f\u673a\u654c\u4eba\u9020\u62105\u7535\u51fb\u4f24\u5bb3",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_battery_delayed": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u7535\u6c60",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 3,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u56de\u5408\u7ed3\u675f\u65f6\u82e5\u6709\u5269\u4f59\u9b54\u529b\u5219\u4e0b\u56de\u5408\u5f00\u59cb\u65f6\u56de\u590d2M",
        "upgrade_text": "\u82b1\u8d39-1\uff0c\u56de\u5408\u7ed3\u675f\u65f6\u82e5\u6709\u5269\u4f59\u9b54\u529b\u5219\u4e0b\u56de\u5408\u5f00\u59cb\u65f6\u56de\u590d2M",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_serration": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u952f\u9f7f",
            "en": ""
        },
        "cost_e": 0,
        "cost_m": 5,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u8fd9\u56de\u5408\u4f60\u9020\u6210\u7684\u4f24\u5bb3\u7ffb\u500d",
        "upgrade_text": "\u589e\u52a0\u4fdd\u7559\uff0c\u8fd9\u56de\u5408\u4f60\u9020\u6210\u7684\u4f24\u5bb3\u7ffb\u500d",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_starfish": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u6d77\u661f",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u53ea\u6709\u4e0a\u56de\u5408\u672a\u53d7\u4f24\u624d\u80fd\u6253\u51fa\uff0c\u83b7\u5f977S\uff0c\u56de\u590d2M",
        "upgrade_text": "\u53ea\u6709\u4e0a\u56de\u5408\u672a\u53d7\u4f24\u624d\u80fd\u6253\u51fa\uff0c\u83b7\u5f9710S\uff0c\u56de\u590d2M",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_honey_shield": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u8702\u871c",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 1,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u83b7\u5f97\uff0812+\u5269\u4f59\u9b54\u529b\uff09S",
        "upgrade_text": "\u83b7\u5f97\uff0816+\u5269\u4f59\u9b54\u529b\uff09S",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_constellation": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u661f\u5ea7",
            "en": ""
        },
        "cost_e": 2,
        "cost_m": 2,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "",
        "base_text": "\u9020\u621034D \u5bf9\u6240\u6709\u624b\u724c\u65bd\u52a0\u4e00\u6682\u65f6\u9b54\u6cd5\u6c89\u91cd",
        "upgrade_text": "\u9020\u621042D \u5bf9\u6240\u6709\u624b\u724c\u65bd\u52a0\u4e00\u6682\u65f6\u9b54\u6cd5\u6c89\u91cd",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_mask": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u53e3\u7f69",
            "en": ""
        },
        "cost_e": 0,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "\u653e\u9010",
        "base_text": "\u672c\u56de\u5408\u4f60\u6bcf\u6d88\u80171M\uff0c\u83b7\u5f973S",
        "upgrade_text": "\u53d6\u6d88\u653e\u9010\uff0c\u672c\u56de\u5408\u4f60\u6bcf\u6d88\u80171M\uff0c\u83b7\u5f973S",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_missile": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u5bfc\u5f39",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 3,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "\u84c4\u52bf\u5f85\u53d1",
        "base_text": "\u9020\u621015D\u62bd3\u5f20\u724c",
        "upgrade_text": "\u9020\u621017D\u62bd4\u5f20\u724c",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_wind": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u98ce",
            "en": ""
        },
        "cost_e": 0,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u4e22\u5f03\u6240\u6709\u65e0M\u6d88\u8017\u7684\u5361\u724c\uff0c\u62bd\u76f8\u540c\u6570\u91cf\u6709M\u6d88\u8017\u7684\u724c",
        "upgrade_text": "\u4e22\u5f03\u6240\u6709\u65e0M\u6d88\u8017\u7684\u5361\u724c\uff0c\u62bd\u6570\u91cf+1\u6709M\u6d88\u8017\u7684\u724c",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_chromosome": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u67d3\u8272\u4f53",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u6bcf\u5f53\u4f60\u56de\u590d\u9b54\u529b\u65f6\uff0c\u83b7\u5f972S",
        "upgrade_text": "\u6bcf\u5f53\u4f60\u56de\u590d\u9b54\u529b\u65f6\uff0c\u83b7\u5f973S",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_rose": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u73ab\u7470",
            "en": ""
        },
        "cost_e": 0,
        "cost_m": 2,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u83b7\u5f979S",
        "upgrade_text": "\u83b7\u5f9712S",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_beeswax": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u8702\u8721",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 2,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u672c\u56de\u5408\u4f60\u7684\u62a4\u76fe\u53d7\u5230\u7684\u4f24\u5bb3\u51cf\u534a\uff0c\u83b7\u5f975S",
        "upgrade_text": "\u672c\u56de\u5408\u4f60\u7684\u62a4\u76fe\u53d7\u5230\u7684\u4f24\u5bb3\u51cf\u534a\uff0c\u83b7\u5f978S",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_balloon": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u6c14\u7403",
            "en": ""
        },
        "cost_e": 0,
        "cost_m": 2,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u62bd3\u5f20\u724c\uff0c\u9009\u62e92\u5f20\u624b\u724c\u7f6e\u5165\u62bd\u724c\u5806\u9876",
        "upgrade_text": "\u62bd4\u5f20\u724c\uff0c\u9009\u62e92\u5f20\u624b\u724c\u7f6e\u5165\u62bd\u724c\u5806\u9876",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_air": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u7a7a\u6c14",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 3,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u7ffb\u500d\u4f60\u7684\u62a4\u76fe",
        "upgrade_text": "\u7ffb\u4e09\u500d\u4f60\u7684\u62a4\u76fe",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "mage_rmb": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u4eba\u6c11\u5e01",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u4e0b\u573a\u6218\u6597\u5f00\u59cb\u65f6\uff0c\u83b7\u5f972M",
        "upgrade_text": "\u589e\u52a0\u4fdd\u7559\uff0c\u4e0b\u573a\u6218\u6597\u5f00\u59cb\u65f6\uff0c\u83b7\u5f972M",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "capacitor": {
        "character_id": "mage",
        "name": {
            "zh": "\u7535\u5bb9\u5668",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u5f53\u4f60\u56e0\u7535\u51fb\u4f24\u5bb3\u800c\u65bd\u52a0\u9759\u7535\u65f6\uff0c\u65bd\u52a0\u91cf\u589e\u52a050%",
        "upgrade_text": "\u5f53\u4f60\u56e0\u7535\u51fb\u4f24\u5bb3\u800c\u65bd\u52a0\u9759\u7535\u65f6\uff0c\u65bd\u52a0\u91cf\u589e\u52a075%",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "battery": {
        "character_id": "mage",
        "name": {
            "zh": "\u7535\u6c60",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u4f60\u88ab\u653b\u51fb\u65f6\uff0c\u5bf9\u76ee\u6807\u65bd\u52a04\u5c42\u9759\u7535",
        "upgrade_text": "\u4f60\u88ab\u653b\u51fb\u65f6\uff0c\u5bf9\u76ee\u6807\u65bd\u52a06\u5c42\u9759\u7535",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "plasma": {
        "character_id": "mage",
        "name": {
            "zh": "\u7b49\u79bb\u5b50\u4f53",
            "en": ""
        },
        "cost_e": 3,
        "cost_m": 0,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "",
        "base_text": "\u9020\u62106\u70b9\u7535\u51fb\u4f24\u5bb35\u6b21",
        "upgrade_text": "\u9020\u62108\u70b9\u7535\u51fb\u4f24\u5bb35\u6b21",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "ruby": {
        "character_id": "mage",
        "name": {
            "zh": "\u7ea2\u5b9d\u77f3",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u6bcf\u6b21\u89e6\u53d1\u9759\u7535\u65f6\uff0c\u9020\u62108D",
        "upgrade_text": "\u6bcf\u6b21\u89e6\u53d1\u9759\u7535\u65f6\uff0c\u9020\u621011D",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_ruby": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u7ea2\u5b9d\u77f3",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u6bcf\u6b21\u89e6\u53d1\u9759\u7535\u65f6\uff0c\u83b7\u5f973S",
        "upgrade_text": "\u6bcf\u6b21\u89e6\u53d1\u9759\u7535\u65f6\uff0c\u83b7\u5f974S",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_capacitor": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u7535\u5bb9\u5668",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u6bcf\u6b21\u89e6\u53d1\u9759\u7535\u65f6\uff0c\u83b7\u5f971M",
        "upgrade_text": "\u83b7\u5f97\u56fa\u6709\uff0c\u6bcf\u6b21\u89e6\u53d1\u9759\u7535\u65f6\uff0c\u83b7\u5f971M",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "copper_rod": {
        "character_id": "mage",
        "name": {
            "zh": "\u94dc\u68d2",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u83b7\u5f978S\uff0c\u5411\u76ee\u6807\u654c\u4eba\u65bd\u52a03\u9759\u7535",
        "upgrade_text": "\u83b7\u5f9710S\uff0c\u5411\u76ee\u6807\u654c\u4eba\u65bd\u52a06\u9759\u7535",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_copper_rod": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u94dc\u68d2",
            "en": ""
        },
        "cost_e": 0,
        "cost_m": 4,
        "card_type": "bloom",
        "type_code": "B",
        "tags_text": "",
        "base_text": "\u7ffb\u500d\u76ee\u6807\u9759\u7535",
        "upgrade_text": "\u7ffb\u4e09\u500d\u76ee\u6807\u9759\u7535",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
        "implementation_status": "authored"
    },
    "mage_lithium": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u9502",
            "en": ""
        },
        "cost_e": 2,
        "cost_m": 0,
        "card_type": "root",
        "type_code": "R",
        "tags_text": "",
        "base_text": "\u5f53\u4f60\u89e6\u53d1\u9759\u7535\u65f6\uff0c\u62bd\u4e00\u5f20\u724c",
        "upgrade_text": "\u82b1\u8d39-1\uff0c\u5f53\u4f60\u89e6\u53d1\u9759\u7535\u65f6\uff0c\u62bd\u4e00\u5f20\u724c",
        "rarity": "ultra",
        "authored_rarity": "\u7a76\u7ea7",
        "implementation_status": "authored"
    },
    "electronic_missile": {
        "character_id": "mage",
        "name": {
            "zh": "\u7535\u5b50\u5bfc\u5f39",
            "en": ""
        },
        "cost_e": 1,
        "cost_m": 0,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "\u84c4\u52bf\u5f85\u53d1",
        "base_text": "\u9020\u62109\u70b9\u7535\u51fb\u4f24\u5bb3\u62bd2\u5f20\u724c",
        "upgrade_text": "\u9020\u621011\u70b9\u7535\u51fb\u4f24\u5bb3\u62bd3\u5f20\u724c",
        "rarity": "common",
        "authored_rarity": "\u666e\u901a",
        "implementation_status": "authored"
    },
    "mage_electronic_missile": {
        "character_id": "mage",
        "name": {
            "zh": "\u9b54\u6cd5\u7535\u5b50\u5bfc\u5f39",
            "en": ""
        },
        "cost_e": 0,
        "cost_m": 2,
        "card_type": "thorn",
        "type_code": "T",
        "tags_text": "\u84c4\u52bf\u5f85\u53d1\uff0c\u56de\u8f6c",
        "base_text": "\u9020\u62105\u70b9\u7535\u51fb\u4f24\u5bb3\uff0c\u62bd\u4e00\u5f20\u724c",
        "upgrade_text": "\u9020\u62107\u70b9\u7535\u51fb\u4f24\u5bb3\uff0c\u62bd\u4e00\u5f20\u724c",
        "rarity": "rare",
        "authored_rarity": "\u7a00\u6709",
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
