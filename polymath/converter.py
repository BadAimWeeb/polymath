import json
import os
import shutil
from polymath import utils

# Helper functions to check model types (Simplified and using English strings)

def is_fishing_rod_model(json_data, file_path=""):
	"""Check if the JSON data represents a fishing rod model."""
	normalized_path = os.path.basename(file_path).lower()
	if normalized_path == "fishing_rod.json":
		return True
	if (json_data.get("parent") == "item/handheld_rod" and
		"overrides" in json_data and
		any("cast" in o.get("predicate", {}) for o in json_data.get("overrides", []))):
		return True
	return False

def get_fishing_rod_model(cmd_value, base_model, cast_model, json_data):
	"""Generate fishing rod model structure for a specific custom model data value."""
	normal_model = None
	cast_model_override = None
	for override in json_data.get("overrides", []):
		predicate = override.get("predicate", {})
		if predicate.get("custom_model_data") == cmd_value:
			if predicate.get("cast", 0) == 1:
				cast_model_override = override["model"]
			elif predicate.get("cast", 0) == 0:
				normal_model = override["model"]
	if not normal_model:
		return None
	return {
		"type": "minecraft:condition",
		"property": "minecraft:fishing_rod/cast",
		"on_false": {"type": "minecraft:model", "model": normal_model},
		"on_true": {"type": "minecraft:model", "model": cast_model_override or normal_model}
	}

def is_shield_model(json_data, file_path=""):
	"""Check if the JSON data represents a shield model."""
	normalized_path = os.path.basename(file_path).lower()
	if normalized_path == "shield.json":
		return True
	if (json_data.get("parent") == "builtin/entity" and
		"overrides" in json_data and
		any("blocking" in o.get("predicate", {}) for o in json_data.get("overrides", []))):
		return True
	return False

def get_shield_model(cmd_value, base_model, blocking_model, json_data):
	"""Generate shield model structure for a specific custom model data value."""
	normal_model = None
	blocking_model_override = None
	for override in json_data.get("overrides", []):
		predicate = override.get("predicate", {})
		if predicate.get("custom_model_data") == cmd_value:
			if predicate.get("blocking", 0) == 1:
				blocking_model_override = override["model"]
			elif "blocking" not in predicate:
				normal_model = override["model"]
	if not normal_model:
		return None
	return {
		"type": "minecraft:condition",
		"property": "minecraft:using_item",
		"on_false": {"type": "minecraft:model", "model": normal_model},
		"on_true": {"type": "minecraft:model", "model": blocking_model_override or normal_model}
	}

def is_head_model(json_data, file_path=""):
	"""Check if the JSON data represents a head/skull model."""
	normalized_path = os.path.basename(file_path).lower()
	head_mappings = {
		"player_head.json": ("player", "minecraft:item/template_skull"),
		"piglin_head.json": ("piglin", "minecraft:item/template_skull"),
		"zombie_head.json": ("zombie", "minecraft:item/template_skull"),
		"creeper_head.json": ("creeper", "minecraft:item/template_skull"),
		"dragon_head.json": ("dragon", "minecraft:item/dragon_head"),
		"wither_skeleton_skull.json": ("wither_skeleton", "minecraft:item/template_skull"),
		"skeleton_skull.json": ("skeleton", "minecraft:item/template_skull")
	}
	if normalized_path in head_mappings:
		return True, head_mappings[normalized_path][0], head_mappings[normalized_path][1]
	return False, None, None

def is_damage_model(json_data):
	"""Check if JSON data represents a damage-based model."""
	if "overrides" not in json_data:
		return False
	for override in json_data.get("overrides", []):
		predicate = override.get("predicate", {})
		if ("damaged" in predicate and "damage" in predicate and
			"custom_model_data" not in predicate):
			return True
	return False

def is_potion_model(json_data, file_path=""):
	"""Check if the JSON data represents a potion model."""
	normalized_path = os.path.basename(file_path).lower()
	potion_files = ["potion.json", "splash_potion.json", "lingering_potion.json"]
	return normalized_path in potion_files

def is_chest_model(json_data, file_path=""):
	"""Check if the JSON data represents a chest or trapped chest model."""
	normalized_path = os.path.basename(file_path).lower()
	if normalized_path == "chest.json":
		return True, "chest"
	elif normalized_path == "trapped_chest.json":
		return True, "trapped_chest"
	return False, None

def has_mixed_custom_damage(json_data):
	"""Check if JSON data contains both custom_model_data and damage predicates."""
	if "overrides" not in json_data:
		return False
	cmd_with_damage = False
	for override in json_data["overrides"]:
		predicate = override.get("predicate", {})
		if ("custom_model_data" in predicate and
			"damaged" in predicate and
			"damage" in predicate):
			cmd_with_damage = True
			break
	return cmd_with_damage

# Conversion functions (Simplified and using English strings)

def convert_damage_model(json_data, base_texture=""):
	"""Convert damage-based model JSON format to the new format."""
	if not base_texture:
		base_texture = json_data.get("textures", {}).get("layer0", "")
		if not base_texture:
			base_texture = json_data.get("parent", "")

	new_format = {
		"model": {
			"type": "range_dispatch",
			"property": "damage",
			"fallback": {"type": "model", "model": base_texture},
			"entries": []
		}
	}
	if "display" in json_data:
		new_format["display"] = json_data["display"]

	damage_overrides = [
		override for override in json_data.get("overrides", [])
		if ("damaged" in override.get("predicate", {}) and
			"damage" in override.get("predicate", {}) and
			"custom_model_data" not in override.get("predicate", {}))
	]
	damage_overrides.sort(key=lambda x: float(x.get("predicate", {}).get("damage", 0)))

	for override in damage_overrides:
		model_path = override["model"]
		if ":" not in model_path:
			model_path = f"minecraft:{model_path}"
		predicate = override.get("predicate", {})
		entry = {
			"threshold": float(predicate["damage"]),
			"model": {"type": "model", "model": model_path}
		}
		new_format["model"]["entries"].append(entry)
	return new_format

def convert_mixed_custom_damage_model(json_data):
	"""Convert a model that has both custom_model_data and damage predicates."""
	base_texture = json_data.get("textures", {}).get("layer0", "")
	parent_path = json_data.get("parent", "")
	base_path = base_texture or parent_path
	if ":" not in base_path and base_path.startswith("item/"):
		base_path = f"minecraft:{base_path}"
	elif ":" not in base_path:
		base_path = f"minecraft:item/{base_path}"

	new_format = {
		"model": {
			"type": "range_dispatch",
			"property": "custom_model_data",
			"fallback": {"type": "model", "model": base_path},
			"entries": []
		}
	}

	cmd_groups = {}
	for override in json_data.get("overrides", []):
		predicate = override.get("predicate", {})
		cmd = predicate.get("custom_model_data")
		if cmd is None: continue
		if cmd not in cmd_groups:
			cmd_groups[cmd] = {"base_model": None, "damage_states": []}
		if "damaged" in predicate and "damage" in predicate:
			cmd_groups[cmd]["damage_states"].append({
				"damage": float(predicate["damage"]),
				"model": override["model"]
			})
		else:
			cmd_groups[cmd]["base_model"] = override["model"]

	for cmd, group in sorted(cmd_groups.items()):
		base_model = group["base_model"] or base_path
		damage_states = sorted(group["damage_states"], key=lambda x: x["damage"])
		cmd_entry = {
			"threshold": int(cmd),
			"model": {
				"type": "range_dispatch",
				"property": "damage",
				"fallback": {"type": "model", "model": base_model},
				"entries": []
			}
		}
		for state in damage_states:
			damage_entry = {
				"threshold": state["damage"],
				"model": {"type": "model", "model": state["model"]}
			}
			cmd_entry["model"]["entries"].append(damage_entry)
		new_format["model"]["entries"].append(cmd_entry)

	if "display" in json_data:
		new_format["display"] = json_data["display"]
	return new_format

def convert_json_format(json_data, is_item_model=False, file_path=""):
	"""Convert JSON format with special handling for different model types."""
	base_texture = json_data.get("textures", {}).get("layer0", "")
	parent_path = json_data.get("parent", "")
	base_path = base_texture or parent_path

	is_potion = is_potion_model(json_data, file_path)
	if is_potion:
		textures = json_data.get("textures", {})
		if textures.get("layer0") == "item/splash_potion_overlay": base_path = "minecraft:item/splash_potion"
		elif textures.get("layer0") == "item/lingering_potion_overlay": base_path = "minecraft:item/lingering_potion"
		else: base_path = "minecraft:item/potion"

	is_chest, chest_type = is_chest_model(json_data, file_path)
	is_head, head_kind, head_base = is_head_model(json_data, file_path)
	is_shield = is_shield_model(json_data, file_path)
	is_fishing_rod = is_fishing_rod_model(json_data, file_path)
	normalized_filename = os.path.basename(file_path).lower()
	filename_without_ext = os.path.splitext(normalized_filename)[0]
	is_bow = (normalized_filename == "bow.json") or (not is_chest and filename_without_ext == "bow")
	is_crossbow = (normalized_filename == "crossbow.json") or (not is_chest and filename_without_ext == "crossbow")

	if has_mixed_custom_damage(json_data):
		return convert_mixed_custom_damage_model(json_data)
	if is_damage_model(json_data):
		return convert_damage_model(json_data, base_path)

	if is_head:
		if not head_base.startswith("minecraft:"): head_base = f"minecraft:{head_base}"
		new_format = {
			"model": {
				"type": "range_dispatch" if not is_item_model else "model",
				"property": "custom_model_data" if not is_item_model else None,
				"fallback": {
					"type": "minecraft:special", "base": head_base,
					"model": {"type": "minecraft:head", "kind": head_kind}
				},
				"entries": [] if not is_item_model else None
			}
		}
		if "display" in json_data: new_format["display"] = json_data["display"]
		if "overrides" in json_data:
			for override in json_data.get("overrides", []):
				if "predicate" in override and "custom_model_data" in override["predicate"]:
					cmd = int(override["predicate"]["custom_model_data"])
					model_path = override["model"]
					if not model_path.startswith("minecraft:") and not ":" in model_path:
						model_path = f"minecraft:item/{model_path}"
					if head_kind == "player":
						entry = {"threshold": cmd, "model": {"type": "minecraft:special", "base": model_path, "model": {"type": "minecraft:head", "kind": head_kind}}}
					else:
						entry = {"threshold": cmd, "model": {"type": "model", "model": model_path}}
					new_format["model"]["entries"].append(entry)
		return new_format
	elif is_chest:
		base_path = f"item/{chest_type}"
	else:
		if base_texture and not is_potion:
			if base_path == "item/crossbow_standby": base_path = "item/crossbow"
			elif base_path == "minecraft:item/crossbow_standby": base_path = "minecraft:item/crossbow"
			if not parent_path:
				if base_path.startswith("minecraft:item/"): pass
				elif base_path.startswith("item/"): base_path = f"minecraft:{base_path}"
				elif not base_path.startswith("minecraft:"): base_path = f"minecraft:item/{base_path}"

	# Define fallback structures
	if is_shield:
		blocking_model = None
		for override in json_data.get("overrides", []):
			if ("predicate" in override and "blocking" in override["predicate"] and
				override["predicate"].get("blocking") == 1 and "custom_model_data" not in override["predicate"]):
				blocking_model = override["model"]; break
		if not blocking_model: blocking_model = "minecraft:item/shield_blocking"
		if not blocking_model.startswith("minecraft:"): blocking_model = f"minecraft:{blocking_model}"
		base_path = "minecraft:item/shield"
		fallback = {
			"type": "minecraft:condition", "property": "minecraft:using_item",
			"on_false": {"type": "minecraft:special", "base": "minecraft:item/shield", "model": {"type": "minecraft:shield"}},
			"on_true": {"type": "minecraft:special", "base": "minecraft:item/shield_blocking", "model": {"type": "minecraft:shield"}}
		}
	elif is_chest:
		fallback = {
			"type": "minecraft:select", "property": "minecraft:local_time", "pattern": "MM-dd",
			"cases": [{"model": {"type": "minecraft:special", "base": base_path, "model": {"type": "minecraft:chest", "texture": "minecraft:christmas"}}, "when": ["12-24", "12-25", "12-26"]}],
			"fallback": {"type": "minecraft:special", "base": base_path, "model": {"type": "minecraft:chest", "texture": "minecraft:normal"}}
		}
	elif is_potion:
		fallback = {"type": "model", "model": base_path, "tints": [{"type": "minecraft:potion", "default": -13083194}]}
	elif is_fishing_rod:
		base_model, cast_model = None, None
		for override in json_data.get("overrides", []):
			predicate = override.get("predicate", {})
			if "custom_model_data" not in predicate:
				if predicate.get("cast", 0) == 1: cast_model = override["model"]
				else: base_model = override["model"]
		if not base_model: base_model = json_data.get("textures", {}).get("layer0", "minecraft:item/fishing_rod")
		if not cast_model: cast_model = "minecraft:item/fishing_rod_cast"
		if not base_model.startswith("minecraft:"): base_model = f"minecraft:{base_model}"
		if not cast_model.startswith("minecraft:"): cast_model = f"minecraft:{cast_model}"
		fallback = {
			"type": "minecraft:condition", "property": "minecraft:fishing_rod/cast",
			"on_false": {"type": "minecraft:model", "model": base_model},
			"on_true": {"type": "minecraft:model", "model": cast_model}
		}
	elif is_bow:
		fallback = {
			"type": "minecraft:condition", "property": "minecraft:using_item",
			"on_false": {"type": "minecraft:model", "model": "minecraft:item/bow"},
			"on_true": {
				"type": "minecraft:range_dispatch", "property": "minecraft:use_duration", "scale": 0.05,
				"fallback": {"type": "minecraft:model", "model": "minecraft:item/bow_pulling_0"},
				"entries": [
					{"threshold": 0.65, "model": {"type": "minecraft:model", "model": "minecraft:item/bow_pulling_1"}},
					{"threshold": 0.9, "model": {"type": "minecraft:model", "model": "minecraft:item/bow_pulling_2"}}
				]
			}
		}
	elif is_crossbow:
		fallback = {
			"type": "minecraft:condition", "property": "minecraft:using_item",
			"on_false": {
				"type": "minecraft:select", "property": "minecraft:charge_type",
				"fallback": {"type": "minecraft:model", "model": "minecraft:item/crossbow"},
				"cases": [
					{"model": {"type": "minecraft:model", "model": "minecraft:item/crossbow_arrow"}, "when": "arrow"},
					{"model": {"type": "minecraft:model", "model": "minecraft:item/crossbow_firework"}, "when": "rocket"}
				]
			},
			"on_true": {
				"type": "minecraft:range_dispatch", "property": "minecraft:crossbow/pull",
				"fallback": {"type": "minecraft:model", "model": "minecraft:item/crossbow_pulling_0"},
				"entries": [
					{"threshold": 0.58, "model": {"type": "minecraft:model", "model": "minecraft:item/crossbow_pulling_1"}},
					{"threshold": 1.0, "model": {"type": "minecraft:model", "model": "minecraft:item/crossbow_pulling_2"}}
				]
			}
		}
	else:
		fallback = {"type": "model", "model": base_path}

	# Create basic structure
	new_format = {
		"model": {
			"type": "range_dispatch" if not is_item_model else "model",
			"property": "custom_model_data" if not is_item_model else None,
			"fallback": fallback,
			"entries": [] if not is_item_model else None
		}
	}
	if "display" in json_data: new_format["display"] = json_data["display"]
	if "overrides" not in json_data: return new_format

	# Handle overrides based on type
	if is_crossbow:
		cmd_groups = {}
		for override in json_data["overrides"]:
			if "predicate" not in override or "model" not in override: continue
			predicate = override["predicate"]; cmd = predicate.get("custom_model_data")
			if cmd is None: continue
			if cmd not in cmd_groups: cmd_groups[cmd] = {"base": None, "pulling_states": [], "arrow": None, "firework": None}
			if "pulling" in predicate: cmd_groups[cmd]["pulling_states"].append({"pull": predicate.get("pull", 0.0), "model": override["model"]})
			elif "charged" in predicate:
				if predicate.get("firework", 0): cmd_groups[cmd]["firework"] = override["model"]
				else: cmd_groups[cmd]["arrow"] = override["model"]
			else: cmd_groups[cmd]["base"] = override["model"]
		for cmd, group in cmd_groups.items():
			pulling_states = sorted(group["pulling_states"], key=lambda x: x.get("pull", 0))
			base_model = group["base"] or (pulling_states[0]["model"] if pulling_states else base_path)
			entry = {
				"threshold": int(cmd),
				"model": {
					"type": "minecraft:condition", "property": "minecraft:using_item",
					"on_false": {"type": "minecraft:select", "property": "minecraft:charge_type", "fallback": {"type": "minecraft:model", "model": base_model}, "cases": []},
					"on_true": {"type": "minecraft:range_dispatch", "property": "minecraft:crossbow/pull", "fallback": {"type": "minecraft:model", "model": pulling_states[0]["model"] if pulling_states else base_model}, "entries": []}
				}
			}
			cases = entry["model"]["on_false"]["cases"]
			if group["arrow"]: cases.append({"model": {"type": "minecraft:model", "model": group["arrow"]}, "when": "arrow"})
			if group["firework"]: cases.append({"model": {"type": "minecraft:model", "model": group["firework"]}, "when": "rocket"})
			if pulling_states:
				entries = entry["model"]["on_true"]["entries"]
				for state in pulling_states[1:]: entries.append({"threshold": state.get("pull", 0.0), "model": {"type": "minecraft:model", "model": state["model"]}})
			new_format["model"]["entries"].append(entry)
	elif is_bow:
		cmd_groups = {}
		for override in json_data["overrides"]:
			if "predicate" not in override or "model" not in override: continue
			predicate = override["predicate"]; cmd = predicate.get("custom_model_data")
			if cmd is None: continue
			if cmd not in cmd_groups: cmd_groups[cmd] = {"base": None, "pulling_states": []}
			if "pulling" in predicate: cmd_groups[cmd]["pulling_states"].append({"pull": predicate.get("pull", 0.0), "model": override["model"]})
			else: cmd_groups[cmd]["base"] = override["model"]
		for cmd, group in cmd_groups.items():
			pulling_states = sorted(group["pulling_states"], key=lambda x: x.get("pull", 0))
			base_model = group["base"] or (pulling_states[0]["model"] if pulling_states else base_path)
			entry = {
				"threshold": int(cmd),
				"model": {
					"type": "minecraft:condition", "property": "minecraft:using_item",
					"on_false": {"type": "minecraft:model", "model": base_model},
					"on_true": {"type": "minecraft:range_dispatch", "property": "minecraft:use_duration", "scale": 0.05, "fallback": {"type": "minecraft:model", "model": base_model}, "entries": []}
				}
			}
			if pulling_states:
				for state in pulling_states:
					if state["model"] != base_model: entry["model"]["on_true"]["entries"].append({"threshold": state.get("pull", 0.0), "model": {"type": "minecraft:model", "model": state["model"]}})
			new_format["model"]["entries"].append(entry)
	else:
		cmd_groups = {}
		for override in json_data.get("overrides", []):
			if "predicate" in override and "custom_model_data" in override["predicate"]:
				cmd = int(override["predicate"]["custom_model_data"])
				model_path = override["model"]
				if is_chest:
					entry = {
						"threshold": cmd,
						"model": {
							"type": "minecraft:select", "property": "minecraft:local_time", "pattern": "MM-dd",
							"cases": [{"model": {"type": "minecraft:special", "base": model_path, "model": {"type": "minecraft:chest", "texture": "minecraft:christmas"}}, "when": ["12-24", "12-25", "12-26"]}],
							"fallback": {"type": "minecraft:special", "base": model_path, "model": {"type": "minecraft:chest", "texture": "minecraft:normal"}}
						}
					}
					new_format["model"]["entries"].append(entry)
				elif is_shield or is_fishing_rod:
					if cmd not in cmd_groups: cmd_groups[cmd] = []
					cmd_groups[cmd].append(override)
				else:
					entry = {"threshold": cmd, "model": {"type": "model", "model": model_path}}
					new_format["model"]["entries"].append(entry)
		if is_shield:
			for cmd in sorted(cmd_groups.keys()):
				shield_entry = get_shield_model(cmd, base_path, blocking_model, json_data)
				if shield_entry: new_format["model"]["entries"].append({"threshold": cmd, "model": shield_entry})
		elif is_fishing_rod:
			for cmd in sorted(cmd_groups.keys()):
				normal_model, cast_model = None, None
				for override in cmd_groups[cmd]:
					predicate = override.get("predicate", {})
					if predicate.get("custom_model_data") == cmd:
						if predicate.get("cast", 0) == 1: cast_model = override["model"]
						else: normal_model = override["model"]
				if normal_model and cast_model:
					entry = {
						"threshold": cmd,
						"model": {
							"type": "minecraft:condition", "property": "minecraft:fishing_rod/cast",
							"on_false": {"type": "minecraft:model", "model": normal_model},
							"on_true": {"type": "minecraft:model", "model": cast_model}
						}
					}
					new_format["model"]["entries"].append(entry)
	return new_format

def convert_item_model_format(json_data, output_path, input_path=""):
	"""Convert JSON format for Item Model mode."""
	if "overrides" not in json_data or not json_data["overrides"]: return None

	if is_fishing_rod_model(json_data, input_path):
		cmd_groups = {}
		for override in json_data["overrides"]:
			if "predicate" not in override or "model" not in override: continue
			predicate = override["predicate"]; cmd = predicate.get("custom_model_data")
			if cmd is None: continue
			if cmd not in cmd_groups: cmd_groups[cmd] = {"cast": None, "normal": None}
			if predicate.get("cast", 0) == 1: cmd_groups[cmd]["cast"] = override["model"]
			else: cmd_groups[cmd]["normal"] = override["model"]
		for cmd, models in cmd_groups.items():
			if not models["normal"] or not models["cast"]: continue
			new_json = {
				"model": {
					"type": "minecraft:condition", "property": "minecraft:fishing_rod/cast",
					"on_false": {"type": "minecraft:model", "model": models["normal"]},
					"on_true": {"type": "minecraft:model", "model": models["cast"]}
				}
			}
			if "display" in json_data: new_json["display"] = json_data["display"]
			normal_model = models["normal"]
			if ":" in normal_model: namespace, path = normal_model.split(":", 1)
			else: namespace, path = "minecraft", normal_model # Assume minecraft namespace if missing
			file_name = os.path.join(output_path, namespace, path + ".json")
			if not file_name.startswith(os.path.join(output_path, 'minecraft', 'item')):
				file_name = os.path.join(output_path, 'minecraft', 'item', os.path.basename(file_name)) # Ensure it's in item

			os.makedirs(os.path.dirname(file_name), exist_ok=True)
			try:
				with open(file_name, 'w', encoding='utf-8') as f:
					json.dump(new_json, f, indent=4)
				print(f"  -> Generated item model: {os.path.relpath(file_name, output_path)}")
			except Exception as e:
				print(f"Error writing item model file {file_name}: {e}")
		return # Fishing rod handled

	cmd_groups = {}
	for override in json_data["overrides"]:
		if "predicate" not in override or "model" not in override: continue
		predicate = override["predicate"]; cmd = predicate.get("custom_model_data")
		if cmd is None: continue
		if cmd not in cmd_groups:
			cmd_groups[cmd] = {"base": None, "damage_states": [], "pulling_states": [], "arrow": None, "firework": None, "blocking_model": None, "has_damage": False}
		if "damage" in predicate and "damaged" in predicate:
			cmd_groups[cmd]["has_damage"] = True
			cmd_groups[cmd]["damage_states"].append({"damage": float(predicate["damage"]), "model": override["model"]})
		elif "pulling" in predicate: cmd_groups[cmd]["pulling_states"].append({"pull": predicate.get("pull", 0.0), "model": override["model"]})
		elif "charged" in predicate:
			if predicate.get("firework", 0): cmd_groups[cmd]["firework"] = override["model"]
			else: cmd_groups[cmd]["arrow"] = override["model"]
		elif "blocking" in predicate:
			if predicate.get("blocking", 0) == 1: cmd_groups[cmd]["blocking_model"] = override["model"]
			else: cmd_groups[cmd]["base"] = override["model"]
		else: cmd_groups[cmd]["base"] = override["model"]

	for cmd, group in cmd_groups.items():
		if not group["base"]:
			print(f"Warning: No base model found for CMD {cmd} in {input_path}, skipping.")
			continue

		model_path = group["base"]
		if ":" in model_path: namespace, path = model_path.split(":", 1)
		else: namespace, path = "minecraft", model_path # Assume minecraft namespace if missing

		# Ensure the output path is within assets/<namespace>/items/
		file_dir = os.path.join(output_path, namespace, "items")
		file_name = os.path.join(file_dir, os.path.basename(path) + ".json")

		os.makedirs(os.path.dirname(file_name), exist_ok=True)

		# Determine structure based on model type
		if is_shield_model(json_data, input_path):
			new_json = {
				"model": {
					"type": "minecraft:condition", "property": "minecraft:using_item",
					"on_false": {"type": "minecraft:model", "model": group["base"]},
					"on_true": {"type": "minecraft:model", "model": group["blocking_model"] or group["base"]}
				}
			}
		elif "crossbow" in model_path.lower():
			pulling_states = sorted(group["pulling_states"], key=lambda x: x.get("pull", 0))
			new_json = {
				"model": {
					"type": "minecraft:condition", "property": "minecraft:using_item",
					"on_false": {"type": "minecraft:select", "property": "minecraft:charge_type", "fallback": {"type": "minecraft:model", "model": group["base"]}, "cases": []},
					"on_true": {"type": "minecraft:range_dispatch", "property": "minecraft:crossbow/pull", "fallback": {"type": "minecraft:model", "model": pulling_states[0]["model"] if pulling_states else group["base"]}, "entries": []}
				}
			}
			cases = new_json["model"]["on_false"]["cases"]
			if group["arrow"]: cases.append({"model": {"type": "minecraft:model", "model": group["arrow"]}, "when": "arrow"})
			if group["firework"]: cases.append({"model": {"type": "minecraft:model", "model": group["firework"]}, "when": "rocket"})
			if pulling_states:
				entries = new_json["model"]["on_true"]["entries"]
				for state in pulling_states[1:]: entries.append({"threshold": state.get("pull", 0.0), "model": {"type": "minecraft:model", "model": state["model"]}})
		elif "bow" in model_path.lower():
			pulling_states = sorted(group["pulling_states"], key=lambda x: x.get("pull", 0))
			new_json = {
				"model": {
					"type": "minecraft:condition", "property": "minecraft:using_item",
					"on_false": {"type": "minecraft:model", "model": group["base"]},
					"on_true": {"type": "minecraft:range_dispatch", "property": "minecraft:use_duration", "scale": 0.05, "fallback": {"type": "minecraft:model", "model": group["base"]}, "entries": []}
				}
			}
			if pulling_states:
				for state in pulling_states:
					if state["model"] != group["base"]: new_json["model"]["on_true"]["entries"].append({"threshold": state.get("pull", 0.0), "model": {"type": "minecraft:model", "model": state["model"]}})
		elif group["has_damage"] and group["damage_states"]:
			damage_states = sorted(group["damage_states"], key=lambda x: x["damage"])
			new_json = {"model": {"type": "range_dispatch", "property": "damage", "fallback": {"type": "model", "model": model_path}, "entries": []}}
			for state in damage_states: new_json["model"]["entries"].append({"threshold": state["damage"], "model": {"type": "model", "model": state["model"]}})
		elif is_potion_model(json_data, input_path):
			new_json = {"model": {"type": "model", "model": model_path, "tints": [{"type": "minecraft:potion", "default": -13083194}]}}
		elif is_chest_model(json_data, input_path)[0]:
			new_json = {
				"model": {
					"type": "minecraft:select", "property": "minecraft:local_time", "pattern": "MM-dd",
					"cases": [{"model": {"type": "minecraft:special", "base": model_path, "model": {"type": "minecraft:chest", "texture": "minecraft:christmas"}}, "when": ["12-24", "12-25", "12-26"]}],
					"fallback": {"type": "minecraft:special", "base": model_path, "model": {"type": "minecraft:chest", "texture": "minecraft:normal"}}
				}
			}
		else: # Normal item
			new_json = {"model": {"type": "model", "model": model_path}}

		if "display" in json_data: new_json["display"] = json_data["display"]

		try:
			with open(file_name, 'w', encoding='utf-8') as f:
				json.dump(new_json, f, indent=4)
			print(f"  -> Generated item model: {os.path.relpath(file_name, output_path)}")
		except Exception as e:
			print(f"Error writing item model file {file_name}: {e}")

def adjust_folder_structure(base_dir):
	"""
	Adjust the folder structure by moving files from models/item to items
	
	Args:
		base_dir (str): Base directory to adjust structure in
	"""
	assets_path = os.path.join(base_dir, "assets", "minecraft")
	models_item_path = os.path.join(assets_path, "models", "item")
	items_path = os.path.join(assets_path, "items")
	
	if os.path.exists(models_item_path):
		# Only count direct files in models/item directory
		total_files = len([f for f in os.listdir(models_item_path) 
						 if os.path.isfile(os.path.join(models_item_path, f))])
		
		if total_files > 0:
			os.makedirs(items_path, exist_ok=True)
			
			# Only process files directly in models/item
			for item in os.listdir(models_item_path):
				src_path = os.path.join(models_item_path, item)
					
				# Skip if it's a directory
				if os.path.isdir(src_path):
					continue

				dst_path = os.path.join(items_path, item)
					
				# Handle existing file
				if os.path.exists(dst_path):
					backup_path = f"{dst_path}.bak"
					shutil.move(dst_path, backup_path)
					
				# Move file
				shutil.move(src_path, dst_path)
			
			# Only remove models/item if it's empty
			if os.path.exists(models_item_path) and not os.listdir(models_item_path):
				shutil.rmtree(models_item_path)

# --- Core Conversion Function ---

def convert_resource_pack(source_pack_path: str, output_path: str):
	"""
	Converts an extracted Minecraft resource pack directory.

	Args:
		source_pack_path: Path to the extracted source resource pack directory.
		output_path: Path where the converted pack directory will be saved.
	"""
	print(f"Starting resource pack conversion...")
	print(f"Source: {source_pack_path}")
	print(f"Output: {output_path}")

	if not os.path.isdir(source_pack_path):
		print(f"Error: Source directory '{source_pack_path}' not found or is not a directory.")
		return

	processed_files_count = 0
	converted_files_count = 0
	copied_files_count = 0

	# Create output directory structure
	os.makedirs(output_path, exist_ok=True)

	# --- Step 1: Copy all files initially ---
	print("\nStep 1: Copying all files...")
	files_to_process = []
	for root, dirs, files in os.walk(source_pack_path):
		relative_path = os.path.relpath(root, source_pack_path)
		output_root = os.path.join(output_path, relative_path)
		os.makedirs(output_root, exist_ok=True)

		for file in files:
			processed_files_count += 1
			source_file = os.path.join(root, file)
			dest_file = os.path.join(output_root, file)
			try:
				if file.lower().endswith('.json'):
					shutil.copy2(source_file, dest_file)
					files_to_process.append((dest_file, source_file)) # Store (output_path, original_input_path)
			except Exception as e:
				print(f"Error copying file {source_file} to {dest_file}: {e}")

	# --- Step 2: Process JSON files based on mode ---
	print(f"\nStep 2: Processing {len(files_to_process)} JSON files...")

	for output_file, source_file_path_for_context in files_to_process:
		relative_path = os.path.relpath(output_file, output_path)
		try:
			with open(output_file, 'r+', encoding='utf-8') as f:
				try:
					json_data = json.load(f)
				except json.JSONDecodeError as jde:
					print(f"Error decoding JSON in {relative_path}: {jde}. Skipping.")
					f.close()
					os.remove(output_file) # Don't copy since we're doing overlays
					continue # Skip this file

				# CMD mode conversion logic
				should_convert = (
					"overrides" in json_data and
					any("custom_model_data" in o.get("predicate", {}) for o in json_data.get("overrides", []))
				)

				if should_convert:
					print(f"  Converting: {relative_path}")
					converted_data = convert_json_format(json_data, is_item_model=False, file_path=source_file_path_for_context)
					f.seek(0)
					json.dump(converted_data, f, indent=4)
					f.truncate()
					converted_files_count += 1
				else:
					# print(f"  Skipping conversion (no CMD): {relative_path}")
					f.close()
					os.remove(output_file) # Don't copy since we're doing overlays

		except Exception as e:
			print(f"Error processing file {output_file}: {e}")
			os.remove(output_file) # Don't copy since we're doing overlays

	print(f"\nStep 3: Removing empty directories...")
	utils.remove_empty_dirs(output_path)

	print(f"\nStep 4: Correcting folder structure...")
	adjust_folder_structure(output_path)

	print("\n--------------------")
	print("Conversion Summary:")
	print(f"- Total Files Processed: {processed_files_count}")
	print(f"- Files Converted/Generated: {converted_files_count}")
	print(f"- Files Copied (Unchanged): {copied_files_count}")
	print(f"- Output Location: {output_path}")
	print("--------------------")
	print("Processing complete!")

# Example Usage (Optional - Can be removed or commented out)
# if __name__ == "__main__":
#	 # Create dummy source structure for testing
#	 src_dir = "test_source_pack"
#	 out_cmd_dir = "test_output_pack_cmd"
#	 out_item_dir = "test_output_pack_item"
#
#	 # Clean up previous runs
#	 if os.path.exists(src_dir): shutil.rmtree(src_dir)
#	 if os.path.exists(out_cmd_dir): shutil.rmtree(out_cmd_dir)
#	 if os.path.exists(out_item_dir): shutil.rmtree(out_item_dir)
#
#	 # Create dummy files
#	 os.makedirs(os.path.join(src_dir, "assets", "minecraft", "models", "item"), exist_ok=True)
#	 os.makedirs(os.path.join(src_dir, "assets", "minecraft", "textures", "item"), exist_ok=True)
#
#	 # Dummy diamond sword with CMD
#	 diamond_sword_data = {
#		 "parent": "item/handheld",
#		 "textures": {"layer0": "item/diamond_sword"},
#		 "overrides": [
#			 {"predicate": {"custom_model_data": 1}, "model": "item/custom_sword_1"},
#			 {"predicate": {"custom_model_data": 2}, "model": "item/custom_sword_2"}
#		 ]
#	 }
#	 with open(os.path.join(src_dir, "assets", "minecraft", "models", "item", "diamond_sword.json"), "w") as f:
#		 json.dump(diamond_sword_data, f, indent=4)
#
#	 # Dummy custom model file (referenced by override)
#	 custom_sword_model = {"parent": "item/handheld", "textures": {"layer0": "item/custom_sword_texture"}}
#	 with open(os.path.join(src_dir, "assets", "minecraft", "models", "item", "custom_sword_1.json"), "w") as f:
#		json.dump(custom_sword_model, f, indent=4)
#
#	 # Dummy texture file
#	 with open(os.path.join(src_dir, "assets", "minecraft", "textures", "item", "custom_sword_texture.png"), "w") as f:
#		 f.write("dummy png data")
#	 with open(os.path.join(src_dir, "assets", "minecraft", "textures", "item", "diamond_sword.png"), "w") as f:
#		 f.write("dummy png data")
#
#	 print("--- Running CMD Conversion Test ---")
#	 convert_resource_pack(src_dir, out_cmd_dir, mode='cmd')
#
#	 print("\n--- Running Item Model Conversion Test ---")
#	 convert_resource_pack(src_dir, out_item_dir, mode='item_model')
#
#	 print("\n--- Test Complete ---")
#	 # You would typically inspect the output directories (test_output_pack_cmd, test_output_pack_item) manually