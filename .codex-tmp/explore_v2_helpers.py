# -*- coding: utf-8 -*-
import io, sys, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import mod_runtime_v2 as rt

for name in ("_control_options", "_picker_instance_ids", "resolve_v2_target", "_player_id",
             "_valid_player", "_to_number", "_to_int", "eval_v2_value", "_sanitize_ui_component"):
    print(name, hasattr(rt, name))
print(rt._control_options.__doc__)
