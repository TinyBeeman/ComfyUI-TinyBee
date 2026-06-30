import os
import random
import glob
import re
import json
json_lib = json  # alias for nodes where 'json' is a local parameter name
import csv as csvlib
import hashlib
import logging
import datetime
from time import time
import numpy as np
import torch
import zipfile
from io import BytesIO, StringIO
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import folder_paths
from comfy.cli_args import args

try:
    from jsonata import Jsonata as _Jsonata
except Exception as _e:
    try:
        # jsonata-python installs the class in the submodule in some versions
        from jsonata.jsonata import Jsonata as _Jsonata
    except Exception:
        import sys as _sys
        print(f"[TinyBee] jsonata-python not available ({_e}). Run: pip install jsonata-python", file=_sys.stderr)
        _Jsonata = None


class _AnyType(str):
    """Wildcard type that matches any ComfyUI type."""
    def __ne__(self, other):
        return False

_ANY = _AnyType("*")

class AlwaysEqualProxy(str):
    def __eq__(self, _):
        return True

    def __ne__(self, _):
        return False

generic_type = AlwaysEqualProxy("*")

_auto_seed_counter: int = 0

def _strip_quotes(value):
    if isinstance(value, str):
        s = value.strip()
        if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
            return s[1:-1]
    return value


def _normalize_image_batch(images):
    """Normalize possible IMAGE input shapes/types to a 4D torch batch [B, H, W, C]."""
    if images is None:
        return torch.zeros((0, 0, 0, 0), dtype=torch.float32)

    if isinstance(images, torch.Tensor):
        batch = images
    elif isinstance(images, np.ndarray):
        batch = torch.from_numpy(images)
    elif isinstance(images, list):
        if len(images) == 0:
            return torch.zeros((0, 0, 0, 0), dtype=torch.float32)
        normalized = [img if isinstance(img, torch.Tensor) else torch.tensor(img) for img in images]
        batch = torch.stack(normalized, dim=0)
    else:
        batch = torch.tensor(images)

    if batch.dim() == 3:
        batch = batch.unsqueeze(0)

    return batch


# ===========================================================================





# LIST MANAGEMENT





# ===========================================================================

class imp_listCountNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "string_list": ("STRING", {"forceInput": True}),
            }
        }

    
    @staticmethod
    def countList(string_list):
        return (len(string_list),)
    
    INPUT_IS_LIST = True
    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("Count",)
    FUNCTION = "countList"
    CATEGORY = "🐝TinyBee/Lists"


class TinyFolderStructure:
    def __init__(self, path):
        self.path = path
        self.subfolders = []
        self.direct_files = []  # Files directly in this folder

    @staticmethod
    def _is_ignored_folder_name(folder_name):
        return str(folder_name).lower() == "_ignore"

    def populateSubfolders(self, file_list):
        # file_list is a list of files with paths.
        # First let's remove any files that are not under self.path
        relevant_files = [f for f in file_list if f.startswith(self.path)]
        
        # Separate files into direct files and files in subfolders
        subfolder_set = set()
        for file_path in relevant_files:
            rel_path = os.path.relpath(file_path, self.path)
            parts = rel_path.split(os.sep)
            if len(parts) == 1:
                # File is directly in this folder
                self.direct_files.append(file_path)
            else:
                # File is in a subfolder
                subfolder = parts[0]
                if TinyFolderStructure._is_ignored_folder_name(subfolder):
                    continue
                subfolder_set.add(subfolder)

        self.subfolders = [TinyFolderStructure(os.path.join(self.path, subfolder)) for subfolder in subfolder_set]
        # Recursively populate subfolders
        for subfolder in self.subfolders:
            subfolder.populateSubfolders(relevant_files)

    def getSubfolders(self):
        return self.subfolders
    
    def getDirectFiles(self):
        return self.direct_files

class imp_randomFileEntryNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "seed": ("INT", {"default": -1, "min": -1, "max": 0xffffffffffffffff, "control_after_generate": True}),
                "file_list": ("STRING", {"forceInput": True}),
            },
            "optional": {
                "even_chance_depth": ("INT", {"default": -1, "min": -1, "max": 100, "forceInput": False, "help": "If > 0, will randomly choose from subfolders to that level of depth, -1 for all levels"}),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        seed = _unwrap_single_value(kwargs.get("seed", -1))
        if seed == -1:
            # Seed -1 means non-deterministic random behavior.
            return float("NaN")
        return _kwargs_digest(kwargs)
    
    @staticmethod
    def getRandomFileEntry(seed, file_list, even_chance_depth=0):
        def is_in_ignored_dir(file_path):
            normalized = os.path.normpath(file_path)
            path_parts = normalized.split(os.sep)
            return any(part.lower() == "_ignore" for part in path_parts if part)

        # Fix: Access list parameters consistently
        seed_value = seed[0] if isinstance(seed, list) else seed
        depth_value = even_chance_depth[0] if isinstance(even_chance_depth, list) else even_chance_depth
        
        if seed_value == -1:
            random.seed()
        else:
            random.seed(seed_value)

        if len(file_list) <= 0:
            return ("",)

        non_ignored_files = [f for f in file_list if not is_in_ignored_dir(f)]
        if len(non_ignored_files) <= 0:
            return ("",)

        if depth_value == 0:
            return (random.choice(non_ignored_files),)
        
        # Fix: Handle potential commonpath error
        try:
            common_root = os.path.commonpath(non_ignored_files)
        except ValueError:
            # Fallback if paths are on different drives
            return (random.choice(non_ignored_files),)
        
        folder_structure = TinyFolderStructure(common_root)
        folder_structure.populateSubfolders(non_ignored_files)

        # Navigate to the target depth or as deep as possible
        current_folder = folder_structure
        depth = 0
        
        if depth_value == -1:
            # For depth -1, navigate randomly to any depth
            while True:
                subfolders = current_folder.getSubfolders()
                if not subfolders:
                    break
                current_folder = random.choice(subfolders)
                print(f"Random folder at depth {depth + 1}: {current_folder.path}")
                depth += 1
            # Pick from all files at this final location
            final_files = [f for f in non_ignored_files if f.startswith(current_folder.path)]
        else:
            # Navigate to the specified depth, collecting a bucket for direct files
            # at each intermediate level so they aren't excluded from selection.
            buckets = []

            while depth < depth_value:
                # Files directly in the current folder get their own bucket
                level_direct = current_folder.getDirectFiles()
                if level_direct:
                    buckets.append(level_direct)
                    print(f"Bucket (depth {depth}): {len(level_direct)} direct files in {current_folder.path}")

                subfolders = current_folder.getSubfolders()
                if not subfolders:
                    # Can't go deeper, stop here
                    break
                current_folder = random.choice(subfolders)
                print(f"Navigating to depth {depth + 1}: {current_folder.path}")
                depth += 1

            # At target depth: one bucket for direct files, one per subfolder
            direct_files = current_folder.getDirectFiles()
            if direct_files:
                buckets.append(direct_files)
                print(f"Bucket (depth {depth}): {len(direct_files)} direct files in {current_folder.path}")

            subfolders = current_folder.getSubfolders()
            for subfolder in subfolders:
                subfolder_files = [f for f in non_ignored_files if f.startswith(subfolder.path)]
                if subfolder_files:
                    buckets.append(subfolder_files)
                    print(f"Bucket: {len(subfolder_files)} files in {subfolder.path}")
            
            # If no buckets were created, fall back to all files from current folder
            if not buckets:
                final_files = [f for f in non_ignored_files if f.startswith(current_folder.path)]
            else:
                # Randomly select one bucket with equal probability
                selected_bucket = random.choice(buckets)
                final_files = selected_bucket
                print(f"Selected bucket with {len(final_files)} files")
        
        if final_files:
            return (random.choice(final_files),)
        
        print("Error: No files found in selected folder depth.")
        # Safer fallback
        return (random.choice(non_ignored_files) if non_ignored_files else "",)

    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("Entry",)
    FUNCTION = "getRandomFileEntry"
    CATEGORY = "🐝TinyBee/Lists"


class imp_randomListEntryNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "seed": ("INT", {"default": -1, "min": -1, "max": 0xffffffffffffffff, "control_after_generate": True}),
                "string_list": ("STRING", {"forceInput": True}),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        seed = _unwrap_single_value(kwargs.get("seed", -1))
        if seed == -1:
            # Seed -1 means non-deterministic random behavior.
            return float("NaN")
        return _kwargs_digest(kwargs)
    
    @staticmethod
    def getRandomListEntry(seed, string_list):
        if (seed[0] == -1):
            # Use the current time as a seed
            random.seed()
        else:
            random.seed(seed[0])

        if (len(string_list) > 0):
            entry = random.choice(string_list)
            return (entry,)
        return ("",)
    
    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("Entry",)
    FUNCTION = "getRandomListEntry"
    CATEGORY = "🐝TinyBee/Lists"

class imp_incrementerNode:
    def __init__(self):
        self.counters = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "start": ("INT", {"default": 0, "min": -4294967296, "max": 4294967296}),
                "end": ("INT", {"default": 4294967296, "min": -4294967296, "max": 4294967296}),
                "step": ("INT", {"default": 1, "min": -4294967296, "max": 4294967296}),
            },
            "optional": {
                "reset_bool": ("BOOLEAN", {"default": False, "label_on": "Reset", "label_off": "Continue"})
            },
            "hidden": {
                "unique_id": "UNIQUE_ID"
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    OUTPUT_NODE = True
    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("counter",)
    FUNCTION = "increment_number"

    CATEGORY = "🐝TinyBee/Util"

    def increment_number(self, start, end, step, reset_bool=False, unique_id=None):
        counter = int(start)
        initialized = False
        if reset_bool and self.counters.__contains__(unique_id):
            self.counters.pop(unique_id)

        if self.counters.__contains__(unique_id):
            initialized = True
            counter = self.counters[unique_id]

        if (initialized):
            counter += step
            if (step > 0 and counter > end):
                # end + 1 -> start, end + 2 -> start + 1, ...
                counter = start + (counter - end - 1)
            elif (step < 0 and counter < start):
                # end - 1 -> start, end - 2 -> start - 1, ...
                # If end is 1, and counter is 0, then counter should be start
                # If end is 1, and counter is -1, then counter should be start - 1
                counter = start - (end - counter - 1)

        self.counters[unique_id] = counter

        # The UI won't update today
        return {
            "result": (counter,),
            "ui": {
                "text": [str(counter)]
            }
        }

class imp_indexedListEntryNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "index": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "string_list": ("STRING", {"forceInput": True}),
            },
            "optional": {
                "allow_wraparound": ("BOOLEAN", {"default": True, "label_on": "Wraparound", "label_off": "Clamp"})
            }
        }
    
    @staticmethod
    def getIndexedListEntry(index, string_list, allow_wraparound=True):
        if (len(string_list) > 0):
            if allow_wraparound[0]:
                idx = index[0] % len(string_list)
            else:
                # REturn "" for out of bounds instead of wrapping
                if index[0] < 0 or index[0] >= len(string_list):
                    return ("",)
                idx = index[0]
            entry = string_list[idx]
            return (entry,)
        return ("",)
    
    INPUT_IS_LIST = (True,)
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("Entry",)
    FUNCTION = "getIndexedListEntry"
    CATEGORY = "🐝TinyBee/Lists"


class imp_randomizeListNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string_list": ("STRING", {"forceInput": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff})
            }
        }

    @staticmethod
    def randomizeList(string_list,seed):
        if not string_list:
            return ([],)
        random.seed(seed[0])
        random.shuffle(string_list)
        return (string_list,)

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("randomized_list",)
    FUNCTION = "randomizeList"
    CATEGORY = "🐝TinyBee/Lists"

class imp_decorateListNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string_list": ("STRING", {"forceInput": True}),
                "prefix": ("STRING", {"default": "", "forceInput": False}),
                "postfix": ("STRING", {"default": "", "forceInput": False}),
                "search_string": ("STRING", {"default": "", "forceInput": False}),
                "replace_string": ("STRING", {"default": "", "forceInput": False}),
            }
        }

    @staticmethod
    def decorateList(string_list, prefix, postfix, search_string, replace_string):
        if not string_list:
            return ([],)
        decorated = [f"{prefix[0]}{item}{postfix[0]}" for item in string_list]
        if search_string[0] and replace_string[0]:
            decorated = [item.replace(search_string[0], replace_string[0]) for item in decorated]
        return (decorated,)

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("decorated_list",)
    FUNCTION = "decorateList"
    CATEGORY = "🐝TinyBee/Lists"

# Split a list at the specified index into two lists
class imp_splitListNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_list": ("STRING", {"forceInput": True}),
                "split_index": ("INT", {"default": 1, "min": 0}),
            }
        }

    @staticmethod
    def splitList(input_list, split_index):
        if not isinstance(input_list, list):
            raise ValueError("Input must be a list.")

        index = split_index[0]
        if index <= 0:
            return ([], input_list)
        if index > len(input_list):
            return (input_list, [])

        return (input_list[:index], input_list[index:])
    

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,True)
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("first_part", "second_part")
    FUNCTION = "splitList"
    CATEGORY = "🐝TinyBee/Lists"


class imp_sortListNode:
    def __init__(self):
        pass

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string_list": ("STRING", {"forceInput": True}),
                "sort_method": (["default", "date", "filename", "parent folder", "full path", "random"], {"default": "default"}),
                "sort_ascending": ("BOOLEAN", {"default": True, "label_on": "Ascending", "label_off": "Descending"}),
                "seed": ("INT", {"default": 0, "min": -1, "max": 0xffffffffffffffff}),
            }
        }

    @staticmethod
    def sortList(string_list,sort_method,sort_ascending,seed):
        if not string_list:
            return ([],)

        if sort_method[0] == "date":
            string_list.sort(key=lambda f: os.path.getmtime(f) if os.path.exists(f) else 0, reverse=not sort_ascending[0])
        elif sort_method[0] == "filename":
            string_list.sort(key=lambda f: os.path.basename(f).lower(), reverse=not sort_ascending[0])
        elif sort_method[0] == "parent folder":
            string_list.sort(key=lambda f: os.path.dirname(f).lower(), reverse=not sort_ascending[0])
        elif sort_method[0] == "full path":
            string_list.sort(key=lambda f: os.path.abspath(f).lower(), reverse=not sort_ascending[0])
        elif sort_method[0] == "random":
            if seed[0] == -1:
                random.seed()
            else:
                random.seed(seed[0])
            random.shuffle(string_list)
        return (string_list,)

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("sorted_list",)
    FUNCTION = "sortList"
    CATEGORY = "🐝TinyBee/Lists"

class imp_filterListNode:
    def __init__(self):
        pass

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string_list": ("STRING", {"forceInput": True}),
                "string_filter": ("STRING", {"default": "", "forceInput": False}),
                "age_filter": ("INT", {"default": -1, "min": -1, "max": 0xffffffffffffffff}),
                "age_filter_unit": (["days", "hours", "minutes"], {"default": "days"}),
                "invert": ("BOOLEAN", {"default": False, "forceInput": False})
            }
        }

    @staticmethod
    def filterList(string_list, string_filter, age_filter, age_filter_unit, invert):
        if not string_list:
            return ([],)

        norm_filter = string_filter[0].replace('\\', '/').lower() if string_filter[0] else ""
        filtered = []
        for item in string_list:
            if norm_filter and norm_filter not in item.replace('\\', '/').lower():
                continue
            if age_filter[0] != -1:
                # age_filter assumes that item is a path to a file
                if not os.path.exists(item):
                    continue
                if age_filter_unit[0] == "days":
                    age_limit = age_filter[0] * 24 * 60 * 60
                elif age_filter_unit[0] == "hours":
                    age_limit = age_filter[0] * 60 * 60
                elif age_filter_unit[0] == "minutes":
                    age_limit = age_filter[0] * 60
                # Apply age limit filtering
                if os.path.getmtime(item) < time() - age_limit:
                    continue

            filtered.append(item)
        if invert[0]:
            all_set = set(string_list)
            filtered_set = set(filtered)
            filtered = list(all_set - filtered_set)
        return (filtered,)


    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filtered_list",)
    FUNCTION = "filterList"
    CATEGORY = "🐝TinyBee/Lists"


class imp_combineListsNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "list_a": ("STRING", {"forceInput": True}),
                "list_b": ("STRING", {"forceInput": True}),
                "operation": (
                    [
                        "OR (Union)",
                        "AND (In both A and B)",
                        "XOR (A or B but not both)",
                        "A minus B",
                        "B minus A",
                        "CONCAT (Union with duplicates)",
                    ],
                    {"default": "OR (Union)"},
                ),
            }
        }

    @staticmethod
    def combineLists(list_a, list_b, operation):
        # Normalize inputs to lists
        a = list_a or []
        b = list_b or []

        op = operation[0] if isinstance(operation, (list, tuple)) else operation

        def union_distinct(x, y):
            seen = set()
            out = []
            for item in list(x) + list(y):
                if item not in seen:
                    seen.add(item)
                    out.append(item)
            return out

        def intersection_distinct(x, y):
            set_y = set(y)
            seen = set()
            out = []
            for item in x:
                if item in set_y and item not in seen:
                    seen.add(item)
                    out.append(item)
            return out

        def symmetric_diff_distinct(x, y):
            set_x = set(x)
            set_y = set(y)
            seen = set()
            out = []
            for item in list(x) + list(y):
                in_x = item in set_x
                in_y = item in set_y
                if (in_x != in_y) and item not in seen:
                    seen.add(item)
                    out.append(item)
            return out

        def a_minus_b(x, y):
            set_y = set(y)
            out = []
            for item in x:
                if item not in set_y:
                    out.append(item)
            return out

        def b_minus_a(x, y):
            return a_minus_b(y, x)

        # Choose operation (allow matching by prefix before space for robustness)
        key = (op or "").split(" ")[0].upper()
        if key == "OR":
            result = union_distinct(a, b)
        elif key == "AND":
            result = intersection_distinct(a, b)
        elif key == "XOR":
            result = symmetric_diff_distinct(a, b)
        elif key == "A":  # "A minus B"
            result = a_minus_b(a, b)
        elif key == "B":  # "B minus A"
            result = b_minus_a(a, b)
        elif key.startswith("CONCAT"):
            result = list(a) + list(b)
        else:
            # Fallback to union for unknown value
            result = union_distinct(a, b)

        return (result,)

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("combined",)
    FUNCTION = "combineLists"
    CATEGORY = "🐝TinyBee/Lists"


class imp_replaceListNode:
    def __init__(self):
        pass

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string_list": ("STRING", {"forceInput": True}),
                "search_string": ("STRING", {"default": "", "forceInput": False}),
                "replace_string": ("STRING", {"default": "", "forceInput": False}),
                "is_regex": ("BOOLEAN", {"default": False})
            }
        }

    @staticmethod
    def replaceList(string_list, search_string, replace_string, is_regex):
        if not string_list:
            return ([],)

        replaced = []
        for item in string_list:
            if is_regex[0]:
                item = re.sub(search_string[0], replace_string[0], item)
            else:
                item = item.replace(search_string[0], replace_string[0])
            replaced.append(item)
        return (replaced,)

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("replaced_list",)
    FUNCTION = "replaceList"
    CATEGORY = "🐝TinyBee/Lists"

class imp_stringToListNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "combined_string": ("STRING", {"default": "", "forceInput": False, "multiline": True}),
                "delimiter": (["comma", "semicolon", "space", "newline", "custom"], {"default": "newline"}),
                "custom_delimiter": ("STRING", {"default": ";", "forceInput": False}),
                "comment_prefix": ("STRING", {"default": "//", "forceInput": False}),
            }
        }

    @staticmethod
    def parseList(combined_string, delimiter, custom_delimiter, comment_prefix="//"):
        # Normalize inputs from ComfyUI conventions (may come as single-item lists)
        if isinstance(delimiter, (list, tuple)) and delimiter:
            delimiter = delimiter[0]
        if isinstance(custom_delimiter, (list, tuple)) and custom_delimiter:
            custom_delimiter = custom_delimiter[0]
        if isinstance(comment_prefix, (list, tuple)):
            comment_prefix = comment_prefix[0] if comment_prefix else "//"

        s = ""
        if isinstance(combined_string, (list, tuple)):
            s = "\n".join(str(x) for x in combined_string)
        elif combined_string is None:
            s = ""
        else:
            s = str(combined_string)

        if comment_prefix:
            s = "\n".join(line for line in s.splitlines() if not line.lstrip().startswith(comment_prefix))

        if delimiter == "comma":
            delim = ","
        elif delimiter == "semicolon":
            delim = ";"
        elif delimiter == "space":
            delim = " "
        elif delimiter == "newline":
            delim = "\n"
        else:
            delim = custom_delimiter or ";"

        parts = [p.strip() for p in s.split(delim) if p.strip()]
        return (parts,)

    INPUT_IS_LIST = False
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("list",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "parseList"
    CATEGORY = "🐝TinyBee/Lists"


class imp_csvParserNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "csv": ("STRING", {"forceInput": True}),
                "has_headers": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "delimiter": ("STRING", {"default": ",", "forceInput": False, "multiline": False}),
            }
        }

    @staticmethod
    def parseCsv(csv, has_headers, delimiter=","):
        csv_text = _unwrap_single_value(csv)
        has_headers_value = bool(_unwrap_single_value(has_headers))
        delimiter_value = _unwrap_single_value(delimiter)

        csv_text = "" if csv_text is None else str(csv_text)
        delimiter_value = "," if delimiter_value is None else str(delimiter_value)
        if delimiter_value == "":
            delimiter_value = ","

        # csv.reader requires a single-character delimiter.
        parse_delimiter = delimiter_value[0]

        rows_parsed = []
        try:
            reader = csvlib.reader(StringIO(csv_text), delimiter=parse_delimiter)
            rows_parsed = [list(r) for r in reader]
        except Exception:
            # Fallback to a minimal splitter if parsing fails
            rows_parsed = [line.split(delimiter_value) for line in csv_text.splitlines()]

        # Keep row output as row strings joined by user-provided delimiter text.
        row_strings = [delimiter_value.join(r) for r in rows_parsed]

        if len(rows_parsed) == 0:
            return ([], [], [])

        if has_headers_value:
            headers = [str(h) for h in rows_parsed[0]]
            data_rows = rows_parsed[1:]
        else:
            data_rows = rows_parsed
            max_cols = max((len(r) for r in data_rows), default=0)
            headers = [str(i) for i in range(max_cols)]

        max_cols = max(max((len(r) for r in data_rows), default=0), len(headers))
        if not has_headers_value and len(headers) < max_cols:
            headers = [str(i) for i in range(max_cols)]

        dict_list = []
        for row in data_rows:
            entry = {}
            for idx in range(max_cols):
                value = row[idx] if idx < len(row) else ""
                idx_key = str(idx)
                entry[idx_key] = value

                if idx < len(headers):
                    header_key = str(headers[idx])
                    entry[header_key] = value

            dict_list.append(entry)

        return (row_strings, dict_list, headers)

    RETURN_TYPES = ("STRING", "OBJECT", "STRING")
    RETURN_NAMES = ("rows", "dict_list", "headers")
    OUTPUT_IS_LIST = (True, True, True)
    FUNCTION = "parseCsv"
    CATEGORY = "🐝TinyBee/Lists"


class imp_dictionaryLookupNode:
    def __init__(self):
        pass

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return _kwargs_digest(kwargs)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "dictionary": ("OBJECT", {"forceInput": True}),
            },
            "optional": {
                "key": ("STRING", {"default": "", "forceInput": False, "multiline": False}),
                "default_value": ("STRING", {"default": "", "forceInput": False, "multiline": False}),
            }
        }

    @staticmethod
    def lookupValue(dictionary, key="", default_value=""):
        dict_value = _unwrap_single_value(dictionary)
        key_value = _unwrap_single_value(key)
        default = _unwrap_single_value(default_value) or ""

        print(f"Lookup node - raw dict input: {dict_value}, key: {key_value}, default: {default}")

        if isinstance(dict_value, str):
            try:
                parsed = json.loads(dict_value)
                dict_value = parsed if isinstance(parsed, dict) else {}
            except Exception:
                dict_value = {}

        if not isinstance(dict_value, dict):
            dict_value = {}

        key_strings = [str(k) for k in dict_value.keys()]

        lookup = default
        if key_value is not None:
            k = str(key_value)
            if k != "" and k in dict_value:
                lookup = str(dict_value.get(k, default))

        print(f"Lookup node - final dict: {dict_value}, returning: {lookup}")
        return (lookup, key_strings)

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("lookup", "keys")
    OUTPUT_IS_LIST = (False, True)
    FUNCTION = "lookupValue"
    CATEGORY = "🐝TinyBee/Dictionaries"

class imp_filterFileExistsListNode:
    def __init__(self):
        pass

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string_list": ("STRING", {"forceInput": True}),
                "source_substring": ("STRING", {"default": "", "forceInput": False}),
                "dest_substring": ("STRING", {"default": "", "forceInput": False}),
                "return_existing": ("BOOLEAN", {"default": True})
            }
        }

    @staticmethod
    def filterFileExistsList(string_list, source_substring, dest_substring, return_existing):
        if not string_list:
            return ([],)

        # Walk through the list, replacing source_substring with dest_substring,
        # removing the extension (and last '.' character), and appending a wildcard.
        # If return_existing is True, only add items that already exist.
        # If return_existing is False, only add items that don't exist.
        filtered = []
        for item in string_list:
            if not os.path.exists(item):
                continue
            if source_substring[0]:
                search_string = item.replace(source_substring[0], dest_substring[0])
            else:
                search_string = item
            
            # Remove the extension and .
            search_string = os.path.splitext(search_string)[0]
            search_string += "*"
            matches = glob.glob(search_string)
            if matches:
                if return_existing[0]:
                    filtered.append(item)
            else:
                if not return_existing[0]:
                    filtered.append(item)

        return (filtered,)

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filtered_files",)
    FUNCTION = "filterFileExistsList"
    CATEGORY = "🐝TinyBee/Lists"


class imp_getListFromFileNode:
    def __init__(self):
        pass

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": "./", "forceInput": False}),
            }
        }

    @staticmethod
    def getListFromFile(file_path):
        if not os.path.exists(file_path):
            return ([],)

        with open(file_path, 'r') as file:
            lines = file.readlines()
        # Strip whitespace and filter out empty lines
        string_list = [line.strip() for line in lines if line.strip()]
        return (string_list,)

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string_list",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "getListFromFile"
    CATEGORY = "🐝TinyBee/Lists"

# New node: Get File List
class imp_getFileListNode:
    def __init__(self):
        pass

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "path": ("STRING", {"default": "./" }),
                "glob_pattern": ("STRING", {"default": "**/*" }),
                "sort_method": (["default", "date", "filename", "parent folder", "full path", "random"], {"default": "default"}),
                "sort_ascending": ("BOOLEAN", {"default": True, "label_on": "Ascending", "label_off": "Descending"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff})
            },
            "optional": {
                "allowed_extensions": ("STRING", {"default": ".jpeg,.jpg,.png,.tiff,.gif,.bmp,.webp"}),
                "dest_path": ("STRING", {"default": "", "forceInput": False})
            }
        }

    @staticmethod
    def is_allowed(filepath, allowed_extensions, dest_path):
        if (dest_path and dest_path.strip() != ""):
            # We want to see if the file's name (without extension) matches any file in dest_path with the same base name (diffeent extension is okay)
            base_name = os.path.splitext(os.path.basename(filepath))[0]
            # Normalize dest_path to handle path separators correctly
            normalized_dest = os.path.normpath(dest_path)
            dest_pattern = os.path.join(normalized_dest, base_name + "*")
            dest_files = glob.glob(dest_pattern)
            if dest_files:
                return False

        if allowed_extensions is None or allowed_extensions.strip() == "":
            return True
        allowed = [ext.strip().lower() for ext in allowed_extensions.split(',') if ext.strip()]
        if not allowed:
            return True
        if any(filepath.lower().endswith(ext) for ext in allowed):
            return True
        return False

    @staticmethod
    def getFileList(path, glob_pattern, sort_method, sort_ascending, seed, allowed_extensions=None, dest_path=""):
        # allowed_extensions: comma-separated string
        if allowed_extensions is None or allowed_extensions.strip() == "":
            allowed = []
        else:
            allowed = [ext.strip().lower() for ext in allowed_extensions.split(',') if ext.strip()]
        pattern = path.rstrip("/\\") + "/" + glob_pattern
        files = glob.glob(pattern, recursive=True)
        if (len(allowed) > 0 or (dest_path and dest_path.strip() != "")):
            filtered = [f for f in files if imp_getFileListNode.is_allowed(f, allowed_extensions, dest_path)]
        else:
            filtered = files

        # Sorting logic
        if sort_method == "date":
            filtered.sort(key=lambda f: os.path.getmtime(f) if os.path.exists(f) else 0, reverse=not sort_ascending)
        elif sort_method == "filename":
            filtered.sort(key=lambda f: os.path.basename(f).lower(), reverse=not sort_ascending)
        elif sort_method == "parent folder":
            filtered.sort(key=lambda f: os.path.dirname(f).lower(), reverse=not sort_ascending)
        elif sort_method == "full path":
            filtered.sort(key=lambda f: os.path.abspath(f).lower(), reverse=not sort_ascending)
        elif sort_method == "random":
            random.seed(seed)
            random.shuffle(filtered)
        # "default" does not sort
        return (filtered,)

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("file_list",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "getFileList"
    CATEGORY = "🐝TinyBee/Lists"

class imp_processPathNameNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "path": ("STRING", {"default": "./"}),
            }
        }

    @staticmethod
    def processPathName(path):
        # Process the path and return the new name
        full_path = os.path.abspath(path)
        path_only, file_name = os.path.split(full_path)
        file_name_base, file_name_ext = os.path.splitext(file_name)
        # A filename might have a tag, which is all the characters before the first - or _ or integer.
        tag_name = ""
        for i, char in enumerate(file_name_base):
            if char in ['-', '_'] or char.isdigit():
                tag_name = file_name_base[:i]
                break
        if not tag_name:
            tag_name = file_name_base
        return (full_path, path_only, file_name_base, file_name_ext, tag_name)

    RETURN_TYPES = ("STRING","STRING","STRING","STRING","STRING")
    RETURN_NAMES = ("full_path","path_only","file_name_base","file_name_ext","tag_name")
    FUNCTION = "processPathName"
    CATEGORY = "🐝TinyBee/Util"



# Filter Words
class imp_filterWordsNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "word_list": ("STRING", {"default": "", "forceInput": False}),
                "description": ("STRING", {"default": "", "forceInput": False}),
            }
        }

    @staticmethod
    def filterWords(word_list, description):
        # Split the word_list by comma, strip whitespace
        words = [w.strip() for w in word_list.split(',') if w.strip()]
        desc = description.lower()
        found = []
        for w in words:
            # Check if the word appears as a whole word in the description
            if w.lower() in desc:
                found.append(w)
        return (', '.join(found),)

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filtered_words",)
    FUNCTION = "filterWords"
    CATEGORY = "🐝TinyBee/Util"


# Seperates a prompt into up to five parts based on newlines (or double newlines if you prefer)
class imp_promptSplitterNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prefix_all": ("STRING", {"default": "", "multiline": False, "forceInput": False}),
                "prompts": ("STRING", {"default": "", "multiline": True, "forceInput": False}),
                "postfix_all": ("STRING", {"default": "", "multiline": False, "forceInput": False}),
                "search_string": ("STRING", {"default": "", "forceInput": False}),
                "replace_string": ("STRING", {"default": "", "forceInput": False}),
            }
        }
    
    @staticmethod
    def splitPrompt(prefix_all, prompts, postfix_all, search_string, replace_string):
            parts = ["", "", "", "", ""]
            negs = ["", "", "", "", ""]
            # Split the prompts by newlines, strip whitespace and skip empty lines after stripping
            lines = [p.strip() for p in prompts.split('\n') if p.strip()]
            iPart = -1
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.lower().startswith("neg:"):
                    if iPart >= 0 and iPart < 5:
                        neg_text = line[4:].strip()
                        if negs[iPart]:
                            negs[iPart] += ", " + neg_text
                        else:
                            negs[iPart] = neg_text
                            logging.info(f"Added negative prompt to part {iPart + 1}: {neg_text}")
                    else:
                        logging.warning(f"Negative prompt found before any positive prompt: {line}")
                elif iPart < 4:
                    iPart += 1
                    if iPart < 5:
                        parts[iPart] = line

            if prefix_all.strip():
                parts = [prefix_all.strip() + " " + p if p else "" for p in parts]
            if postfix_all.strip():
                parts = [p + " " + postfix_all.strip() if p else "" for p in parts]
            if search_string:
                parts = [p.replace(search_string, replace_string) if p else "" for p in parts]
                negs = [n.replace(search_string, replace_string) if n else "" for n in negs]

            # Ensure all outputs are strings, never None
            safe_parts = [(p if p is not None else "") for p in parts]
            safe_negs = [(n if n is not None else "") for n in negs]
            return (
                safe_parts[0], safe_negs[0],
                safe_parts[1], safe_negs[1],
                safe_parts[2], safe_negs[2],
                safe_parts[3], safe_negs[3],
                safe_parts[4], safe_negs[4]
            )

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("prompt1", "neg1", "prompt2", "neg2", "prompt3", "neg3", "prompt4", "neg4", "prompt5", "neg5")
    # Mark each output explicitly as a non-list scalar to match all five outputs
    OUTPUT_IS_LIST = (False, False, False, False, False, False, False, False, False, False)
    FUNCTION = "splitPrompt"
    CATEGORY = "🐝TinyBee/Util"


class imp_promptSplitterDynamicNode:
    MAX_PROMPT_PAIRS = 32

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prefix_all": ("STRING", {"default": "", "multiline": False, "forceInput": False}),
                "prompts": ("STRING", {"default": "", "multiline": True, "forceInput": False}),
                "postfix_all": ("STRING", {"default": "", "multiline": False, "forceInput": False}),
                "search_string": ("STRING", {"default": "", "forceInput": False}),
                "replace_string": ("STRING", {"default": "", "forceInput": False}),
            }
        }

    @staticmethod
    def _parse_prompt_entries(prefix_all, prompts, postfix_all, search_string, replace_string):
        entries = []
        current_prompt = ""
        current_negs = []

        def finalize_entry():
            nonlocal current_prompt, current_negs
            if not current_prompt:
                return

            prompt_text = current_prompt.strip()
            neg_text = ", ".join(n for n in current_negs if n)

            if prefix_all.strip():
                prompt_text = f"{prefix_all.strip()} {prompt_text}" if prompt_text else prefix_all.strip()
            if postfix_all.strip():
                prompt_text = f"{prompt_text} {postfix_all.strip()}" if prompt_text else postfix_all.strip()
            if search_string:
                prompt_text = prompt_text.replace(search_string, replace_string)
                neg_text = neg_text.replace(search_string, replace_string)

            entries.append((prompt_text or "", neg_text or ""))
            current_prompt = ""
            current_negs = []

        for raw_line in prompts.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.lower().startswith("neg:"):
                if current_prompt:
                    neg_text = line[4:].strip()
                    if neg_text:
                        current_negs.append(neg_text)
                else:
                    logging.warning(f"Negative prompt found before any positive prompt: {line}")
                continue

            finalize_entry()
            current_prompt = line

        finalize_entry()
        return entries

    @staticmethod
    def splitPrompt(prefix_all, prompts, postfix_all, search_string, replace_string):
        entries = imp_promptSplitterDynamicNode._parse_prompt_entries(
            prefix_all, prompts, postfix_all, search_string, replace_string
        )

        max_pairs = imp_promptSplitterDynamicNode.MAX_PROMPT_PAIRS
        padded_entries = entries[:max_pairs]
        while len(padded_entries) < max_pairs:
            padded_entries.append(("", ""))

        outputs = []
        for prompt_text, neg_text in padded_entries:
            outputs.extend([prompt_text, neg_text])

        return tuple(outputs)

    RETURN_TYPES = tuple(["STRING", "STRING"] * MAX_PROMPT_PAIRS)
    RETURN_NAMES = tuple(
        name
        for index in range(1, MAX_PROMPT_PAIRS + 1)
        for name in (f"prompt{index}", f"neg{index}")
    )
    OUTPUT_IS_LIST = tuple([False] * (MAX_PROMPT_PAIRS * 2))
    FUNCTION = "splitPrompt"
    CATEGORY = "🐝TinyBee/Util"

# ===========================================================================





# CASTING AND UTILITIES





# ===========================================================================

class imp_timestampNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    @staticmethod
    def encode_base62(num):
        chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        if num == 0:
            return chars[0]
        arr = []
        base = 62
        while num:
            num, rem = divmod(num, base)
            arr.append(chars[rem])
        arr.reverse()
        return ''.join(arr)

    @staticmethod
    def getTimestamp():
        now = datetime.datetime.now()
        long_fmt = now.strftime("%Y-%m-%d-%H-%M-%S")
        date_fmt = now.strftime("%Y-%m-%d")
        time_fmt = now.strftime("%H-%M-%S")
        short_raw = now.strftime("%y%m%d%H%M%S")  # e.g. 250919135602
        short_int = int(short_raw)
        short_encoded = imp_timestampNode.encode_base62(short_int)
        return (long_fmt, date_fmt, time_fmt, short_encoded)

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("long", "date", "time", "short")
    FUNCTION = "getTimestamp"
    CATEGORY = "🐝TinyBee/Util"


class imp_tinyRandomNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "min": ("FLOAT", {"default": 0.0, "step": 0.01}),
                "max": ("FLOAT", {"default": 1.0, "step": 0.01}),
                "power": ("INT", {"default": 1, "min": 1, "max": 10}),
                "precision": ("INT", {"default": 3, "min": 0, "max": 15}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
            }
        }

    @staticmethod
    def getTinyRandom(min, max, power, precision, seed):
        min_value = float(_unwrap_single_value(min))
        max_value = float(_unwrap_single_value(max))
        power_value = int(_unwrap_single_value(power))
        precision_value = int(_unwrap_single_value(precision))
        seed_value = int(_unwrap_single_value(seed))

        if power_value < 1:
            power_value = 1
        if power_value > 10:
            power_value = 10

        if precision_value < 0:
            precision_value = 0
        if precision_value > 15:
            precision_value = 15

        rng = random.Random(seed_value)
        values = [rng.uniform(min_value, max_value) for _ in range(power_value)]
        avg_value = sum(values) / float(power_value)

        rnd_float = round(avg_value, precision_value)
        if rnd_float == 0:
            rnd_float = 0.0
        rnd_int = int(rnd_float)

        rnd_str = f"{rnd_float:.{precision_value}f}" if precision_value > 0 else str(int(round(rnd_float)))
        if precision_value > 0:
            rnd_str = rnd_str.rstrip("0").rstrip(".")
        if rnd_str == "-0":
            rnd_str = "0"

        return (rnd_int, rnd_float, rnd_str)

    RETURN_TYPES = ("INT", "FLOAT", "STRING")
    RETURN_NAMES = ("rnd_int", "rnd_float", "rnd_str")
    FUNCTION = "getTinyRandom"
    CATEGORY = "🐝TinyBee/Util"

class imp_randomizeImageBatchNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_batch": ("IMAGE", {"forceInput": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff})
            }
        }

    @staticmethod
    def randomizeImageBatch(image_batch, seed):
        if image_batch is None or len(image_batch) == 0:
            return (image_batch,)
        
        # Convert to torch tensor if not already
        if isinstance(image_batch, np.ndarray):
            image_batch = torch.from_numpy(image_batch)
        elif not isinstance(image_batch, torch.Tensor):
            # If it's a list, stack into tensor
            if isinstance(image_batch, list):
                image_batch = torch.stack([torch.tensor(img) if not isinstance(img, torch.Tensor) else img for img in image_batch])
            else:
                image_batch = torch.tensor(image_batch)
        
        # Set random seed and shuffle indices
        random.seed(seed)
        batch_size = image_batch.shape[0]
        indices = list(range(batch_size))
        random.shuffle(indices)
        
        # Reorder the batch using the shuffled indices
        randomized_batch = image_batch[indices]
        
        return (randomized_batch,)

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("randomized_image_batch",)
    FUNCTION = "randomizeImageBatch"
    CATEGORY = "🐝TinyBee/Images"


class imp_imagesFromBatchNode:
    MAX_OUTPUT_IMAGES = 32

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", {"forceInput": True}),
                # Use snake_case as canonical widget/input key for better workflow
                # serialization stability.
                "img_count": ("INT", {"default": 4, "min": 0, "max": cls.MAX_OUTPUT_IMAGES}),
            }
        }

    @staticmethod
    def imagesFromBatch(images, img_count=4):
        batch = _normalize_image_batch(images)

        requested_count = img_count[0] if isinstance(img_count, (list, tuple)) else img_count
        requested_count = requested_count[0] if isinstance(requested_count, (list, tuple)) else requested_count
        requested_count = max(1, min(imp_imagesFromBatchNode.MAX_OUTPUT_IMAGES, int(requested_count)))

        provided_count = int(batch.shape[0]) if batch.dim() > 0 else 0

        if provided_count > 0:
            fallback = batch[provided_count - 1:provided_count].clone()
        else:
            fallback = torch.zeros((1, 64, 64, 3), dtype=torch.float32)

        outputs = []
        for index in range(imp_imagesFromBatchNode.MAX_OUTPUT_IMAGES):
            if index < requested_count and index < provided_count:
                outputs.append(batch[index:index + 1].clone())
            elif index < requested_count:
                outputs.append(fallback.clone())
            else:
                outputs.append(fallback.clone())

        return tuple(outputs)

    RETURN_TYPES = tuple(["IMAGE"] * MAX_OUTPUT_IMAGES)
    RETURN_NAMES = tuple([f"img{index}" for index in range(MAX_OUTPUT_IMAGES)])
    FUNCTION = "imagesFromBatch"
    CATEGORY = "🐝TinyBee/Images"


class imp_gridDividerNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "grid_image": ("IMAGE", {"forceInput": True}),
                "cols": ("INT", {"default": 2, "min": 1, "max": 4096}),
                "rows": ("INT", {"default": 2, "min": 1, "max": 4096}),
            }
        }

    @staticmethod
    def divideGrid(grid_image, cols, rows):
        if grid_image is None:
            return (torch.zeros((1, 64, 64, 3), dtype=torch.float32), 64, 64)

        # Normalize to tensor in Comfy image format [B, H, W, C]
        if isinstance(grid_image, np.ndarray):
            grid_image = torch.from_numpy(grid_image)
        elif not isinstance(grid_image, torch.Tensor):
            if isinstance(grid_image, list):
                grid_image = torch.stack([
                    torch.tensor(img) if not isinstance(img, torch.Tensor) else img
                    for img in grid_image
                ])
            else:
                grid_image = torch.tensor(grid_image)

        if grid_image.dim() == 3:
            grid_image = grid_image.unsqueeze(0)

        # Ensure values are plain ints if they are wrapped
        if isinstance(cols, (list, tuple)):
            cols = cols[0] if cols else 1
        if isinstance(rows, (list, tuple)):
            rows = rows[0] if rows else 1

        cols = max(1, int(cols))
        rows = max(1, int(rows))

        _, image_height, image_width, _ = grid_image.shape
        cell_width = max(1, image_width // cols)
        cell_height = max(1, image_height // rows)

        cells = []
        for image in grid_image:
            for r in range(rows):
                y0 = r * cell_height
                y1 = y0 + cell_height
                for c in range(cols):
                    x0 = c * cell_width
                    x1 = x0 + cell_width
                    cells.append(image[y0:y1, x0:x1, :])

        if not cells:
            return (torch.zeros((1, 64, 64, 3), dtype=torch.float32), cell_width, cell_height)

        images = torch.stack(cells, dim=0)
        return (images, cell_width, cell_height)

    RETURN_TYPES = ("IMAGE", "INT", "INT")
    RETURN_NAMES = ("images", "cell_width", "cell_height")
    FUNCTION = "divideGrid"
    CATEGORY = "🐝TinyBee/Images"


class imp_gridMakerDynamicNode:
    MAX_ROWS_COLS = 10

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        optional_inputs = {}
        for row in range(cls.MAX_ROWS_COLS):
            for col in range(cls.MAX_ROWS_COLS):
                optional_inputs[f"img_{row}_{col}"] = ("IMAGE", {"default": None, "forceInput": True})

        return {
            "required": {
                "rows": ("INT", {"default": 2, "min": 1, "max": cls.MAX_ROWS_COLS}),
                "cols": ("INT", {"default": 2, "min": 1, "max": cls.MAX_ROWS_COLS}),
            },
            "optional": optional_inputs,
        }

    @staticmethod
    def _unwrap_scalar(value, default):
        if isinstance(value, (list, tuple)):
            if len(value) == 0:
                return default
            return value[0]
        return value if value is not None else default

    @staticmethod
    def _extract_single_image(image_value):
        if image_value is None:
            return None

        batch = _normalize_image_batch(image_value)
        if not isinstance(batch, torch.Tensor) or batch.dim() != 4 or batch.shape[0] <= 0:
            return None

        return batch[0]

    @staticmethod
    def _fit_to_cell(image, cell_height, cell_width, channels, dtype, device):
        out = torch.zeros((cell_height, cell_width, channels), dtype=dtype, device=device)
        if image is None:
            return out

        img = image
        if not isinstance(img, torch.Tensor):
            try:
                img = torch.tensor(img)
            except Exception:
                return out

        if img.dim() == 2:
            img = img.unsqueeze(-1)
        elif img.dim() > 3:
            # If unexpected batch-like shape leaks through, take first slice.
            img = img[0]
            if img.dim() == 2:
                img = img.unsqueeze(-1)

        if img.dim() != 3:
            return out

        img = img.to(device=device, dtype=dtype)

        if img.shape[-1] < channels:
            channel_pad = channels - int(img.shape[-1])
            img = torch.cat(
                [img, torch.zeros((img.shape[0], img.shape[1], channel_pad), dtype=dtype, device=device)],
                dim=-1,
            )
        elif img.shape[-1] > channels:
            img = img[..., :channels]

        copy_h = min(cell_height, int(img.shape[0]))
        copy_w = min(cell_width, int(img.shape[1]))
        out[:copy_h, :copy_w, :] = img[:copy_h, :copy_w, :]
        return out

    @staticmethod
    def makeGrid(rows, cols, **kwargs):
        max_dim = imp_gridMakerDynamicNode.MAX_ROWS_COLS
        rows_value = int(imp_gridMakerDynamicNode._unwrap_scalar(rows, 1))
        cols_value = int(imp_gridMakerDynamicNode._unwrap_scalar(cols, 1))
        rows_value = max(1, min(max_dim, rows_value))
        cols_value = max(1, min(max_dim, cols_value))

        reference = imp_gridMakerDynamicNode._extract_single_image(kwargs.get("img_0_0"))
        if reference is None:
            # Fallback to first provided image to infer cell shape.
            for row in range(rows_value):
                found = False
                for col in range(cols_value):
                    reference = imp_gridMakerDynamicNode._extract_single_image(kwargs.get(f"img_{row}_{col}"))
                    if reference is not None:
                        found = True
                        break
                if found:
                    break

        if reference is None:
            cell_height, cell_width, channels = 64, 64, 3
            dtype = torch.float32
            device = "cpu"
        else:
            cell_height = int(reference.shape[0])
            cell_width = int(reference.shape[1])
            channels = int(reference.shape[2]) if reference.dim() == 3 else 3
            dtype = reference.dtype
            device = reference.device

        row_images = []
        for row in range(rows_value):
            col_images = []
            for col in range(cols_value):
                img_name = f"img_{row}_{col}"
                image = imp_gridMakerDynamicNode._extract_single_image(kwargs.get(img_name))
                fitted = imp_gridMakerDynamicNode._fit_to_cell(
                    image,
                    cell_height=cell_height,
                    cell_width=cell_width,
                    channels=channels,
                    dtype=dtype,
                    device=device,
                )
                col_images.append(fitted)
            row_images.append(torch.cat(col_images, dim=1))

        grid = torch.cat(row_images, dim=0).unsqueeze(0)
        return (grid, cell_width, cell_height)

    RETURN_TYPES = ("IMAGE", "INT", "INT")
    RETURN_NAMES = ("grid_image", "cell_width", "cell_height")
    FUNCTION = "makeGrid"
    CATEGORY = "🐝TinyBee/Images"

class imp_forceAspectOnBoundsNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "x": ("INT", {"default": 0, "min": -10000, "max": 10000}),
                "y": ("INT", {"default": 0, "min": -10000, "max": 10000}),
                "width": ("INT", {"default": 512, "min": 1, "max": 10000}),
                "height": ("INT", {"default": 512, "min": 1, "max": 10000}),
                "image_width": ("INT", {"default": 512, "min": 1, "max": 10000}),
                "image_height": ("INT", {"default": 512, "min": 1, "max": 10000}),
                "aspect_ratio": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 100.0, "step": 0.01}),
                "fit_mode": (["maintain_height", "maintain_width"], {"default": "maintain_height"})
            },
            "optional": {
                "include_x": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
                "include_y": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
                "include_width": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
                "include_height": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
                "include_rel_xy": ("BOOLEAN", {"default": False, "label_on": "Relative to (x,y)", "label_off": "Relative to (0,0)"}),
            }
        }

    # Lightweight rectangle helper for internal clarity
    class _Rect:
        __slots__ = ("x", "y", "w", "h")

        def __init__(self, x: float, y: float, w: float, h: float):
            self.x = float(x)
            self.y = float(y)
            self.w = float(max(0.0, w))
            self.h = float(max(0.0, h))

        @staticmethod
        def from_xywh(x, y, w, h):
            return imp_forceAspectOnBoundsNode._Rect(x, y, w, h)

        def copy(self):
            return imp_forceAspectOnBoundsNode._Rect(self.x, self.y, self.w, self.h)

        @property
        def right(self):
            return self.x + self.w

        @property
        def bottom(self):
            return self.y + self.h

        @property
        def cx(self):
            return self.x + self.w / 2.0

        @property
        def cy(self):
            return self.y + self.h / 2.0

        def set_center(self, cx, cy):
            self.x = float(cx) - self.w / 2.0
            self.y = float(cy) - self.h / 2.0
            return self

        def clamp_inside_image(self, iw, ih):
            # Ensure the rect lies fully within image bounds if possible
            max_x = max(0.0, iw - self.w)
            max_y = max(0.0, ih - self.h)
            self.x = min(max(self.x, 0.0), max_x)
            self.y = min(max(self.y, 0.0), max_y)
            return self

        def union(self, other):
            x1 = min(self.x, other.x)
            y1 = min(self.y, other.y)
            x2 = max(self.right, other.right)
            y2 = max(self.bottom, other.bottom)
            return imp_forceAspectOnBoundsNode._Rect(x1, y1, x2 - x1, y2 - y1)

        def includes(self, other):
            return self.x <= other.x and self.y <= other.y and self.right >= other.right and self.bottom >= other.bottom

        def size_fit_aspect(self, aspect, fit_mode, iw, ih):
            # Compute new size with requested aspect, preserving one dimension per fit_mode,
            # then scale-down uniformly to fit image if needed; returns a new rect centered
            # at current center.
            ar = float(aspect)
            if ar <= 0:
                ar = 1.0
            if fit_mode == "maintain_height":
                new_h = max(1.0, self.h)
                new_w = new_h * ar
            else:
                new_w = max(1.0, self.w)
                new_h = new_w / ar

            # If exceeds image, scale down uniformly
            if new_w > iw or new_h > ih:
                scale = min(iw / new_w, ih / new_h, 1.0)
                new_w *= scale
                new_h *= scale

            # Round to integers and enforce exact aspect by deriving h from w,
            # falling back to deriving w from h if height would overflow.
            new_w = min(iw, max(1, int(round(new_w))))
            new_h = max(1, int(round(new_w / ar)))
            if new_h > ih:
                new_h = min(ih, new_h)
                new_w = min(iw, max(1, int(round(new_h * ar))))
                new_h = max(1, int(round(new_w / ar)))
                if new_h > ih:
                    new_h = ih
                    new_w = max(1, min(iw, int(round(new_h * ar))))

            r = self.copy()
            r.w = float(new_w)
            r.h = float(new_h)
            r.set_center(self.cx, self.cy)
            return r

        def shift_to_include(self, inc, iw, ih):
            # Shift horizontally to include inc as much as possible
            max_x_pos = max(0.0, iw - self.w)
            max_y_pos = max(0.0, ih - self.h)

            # Horizontal
            if inc.w <= self.w:
                fully_low = inc.x + inc.w - self.w
                fully_high = inc.x
                feasible_low = max(0.0, fully_low)
                feasible_high = min(max_x_pos, fully_high)
                if feasible_low <= feasible_high:
                    if self.x < feasible_low:
                        self.x = feasible_low
                    elif self.x > feasible_high:
                        self.x = feasible_high
                else:
                    target_x = inc.cx - self.w / 2.0
                    self.x = min(max(target_x, 0.0), max_x_pos)
            else:
                target_x = inc.cx - self.w / 2.0
                self.x = min(max(target_x, 0.0), max_x_pos)

            # Vertical
            if inc.h <= self.h:
                fully_low_y = inc.y + inc.h - self.h
                fully_high_y = inc.y
                feasible_low_y = max(0.0, fully_low_y)
                feasible_high_y = min(max_y_pos, fully_high_y)
                if feasible_low_y <= feasible_high_y:
                    if self.y < feasible_low_y:
                        self.y = feasible_low_y
                    elif self.y > feasible_high_y:
                        self.y = feasible_high_y
                else:
                    target_y = inc.cy - self.h / 2.0
                    self.y = min(max(target_y, 0.0), max_y_pos)
            else:
                target_y = inc.cy - self.h / 2.0
                self.y = min(max(target_y, 0.0), max_y_pos)

            return self

    @staticmethod
    def forceAspectOnBounds(x, y, width, height, image_width, image_height, aspect_ratio, fit_mode, 
                            include_x=0, include_y=0, include_width=0, include_height=0, include_rel_xy=False):
        """Adjust a bounding box to the desired aspect ratio while ensuring it fits inside
        the provided image dimensions. Start from the union of the original rect and the
        include rect (if any), then size to aspect, clamp within the image, and shift only
        as needed to include as much of the include rect as possible. Parameters remain
        unchanged and return types are (INT, INT, INT, INT).
        """

        iw = int(image_width)
        ih = int(image_height)

        # Basic guards
        if iw <= 0 or ih <= 0:
            return (int(x), int(y), int(max(1, width)), int(max(1, height)))

        ar = float(aspect_ratio) if aspect_ratio is not None else 0.0
        if ar <= 0.0:
            # No aspect enforcement: just clamp original within image
            nx = max(0, min(int(x), iw - 1))
            ny = max(0, min(int(y), ih - 1))
            nw = max(1, min(int(width), iw - nx))
            nh = max(1, min(int(height), ih - ny))
            return (nx, ny, nw, nh)

        src = imp_forceAspectOnBoundsNode._Rect.from_xywh(x, y, width, height)

        # Build include rect if requested
        must_include = (include_width > 0 and include_height > 0)
        if must_include:
            inc_x = include_x + (x if include_rel_xy else 0)
            inc_y = include_y + (y if include_rel_xy else 0)
            inc = imp_forceAspectOnBoundsNode._Rect.from_xywh(inc_x, inc_y, include_width, include_height)
            # Clamp include to image bounds (non-empty)
            inc.x = max(0.0, min(inc.x, iw - 1))
            inc.y = max(0.0, min(inc.y, ih - 1))
            inc.w = max(1.0, min(inc.w, iw - inc.x))
            inc.h = max(1.0, min(inc.h, ih - inc.y))

            # Start from the union
            base = src.union(inc)
            # If union already covers the entire image, return full image
            if base.w >= iw and base.h >= ih:
                return (0, 0, iw, ih)
        else:
            base = src
            inc = None

        # Size to aspect around base's center, then clamp inside image
        sized = base.size_fit_aspect(ar, fit_mode, iw, ih)
        sized.clamp_inside_image(iw, ih)

        # If we must include an include-rect, shift only as needed to include it fully,
        # or otherwise maximize overlap while staying within image bounds.
        if must_include and inc is not None:
            if not sized.includes(inc):
                sized.shift_to_include(inc, iw, ih)

        # Final integer outputs
        out_x = int(round(sized.x))
        out_y = int(round(sized.y))
        out_w = int(round(sized.w))
        out_h = int(round(sized.h))

        # Final safety clamps & exact aspect enforcement after rounding
        out_w = min(iw, max(1, out_w))
        out_h = max(1, int(round(out_w / ar)))
        if out_h > ih:
            out_h = min(ih, out_h)
            out_w = min(iw, max(1, int(round(out_h * ar))))
            out_h = max(1, int(round(out_w / ar)))
            if out_h > ih:
                out_h = ih
                out_w = max(1, min(iw, int(round(out_h * ar))))

        max_x = iw - out_w
        max_y = ih - out_h
        out_x = min(max(out_x, 0), max_x)
        out_y = min(max(out_y, 0), max_y)

        return (out_x, out_y, out_w, out_h)

    RETURN_TYPES = ("INT", "INT", "INT", "INT")
    RETURN_NAMES = ("new_x", "new_y", "new_width", "new_height")
    FUNCTION = "forceAspectOnBounds"
    CATEGORY = "🐝TinyBee/Util"

class imp_selectBoundingBoxNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE", {"default": None}),
                "data": ("JSON", ),
                "index": ("STRING", {"default": "", "forceInput": False}),
                "method": (["biggest", "center", "balanced"], {"default": "balanced", "forceInput": False}),
            },
            
        }
    
    RETURN_TYPES = ("STRING", "BBOX")
    RETURN_NAMES =("center_coordinates", "bboxes")
    FUNCTION = "segment"
    CATEGORY = "🐝TinyBee/Util"

    def segment(self, image, data, index, method):
        # Basic validation of input data structure
        if not data:
            # Match Florence2toCoordinates: first return is a JSON string (array of center dicts), second is list of bboxes
            return (json.dumps([{"x": 0, "y": 0}]), [])

        # Helper to extract bbox list from a possible dict
        def get_bboxes(item):
            if isinstance(item, dict) and "bboxes" in item:
                return item["bboxes"]
            return item

        try:
            primary = get_bboxes(data[0]) if isinstance(data, (list, tuple)) and len(data) > 0 else []
        except Exception:
            primary = []

        if not isinstance(primary, list):
            primary = []

        # Parse indices (comma separated). If none valid, fallback to all.
        indexes = []
        if isinstance(index, str) and index.strip():
            for token in [t.strip() for t in index.split(',') if t.strip()]:
                try:
                    iv = int(token)
                    indexes.append(iv)
                except ValueError:
                    # Ignore invalid tokens
                    pass
        if not indexes:
            indexes = list(range(len(primary)))

        # Collect valid bboxes from requested indices
        selected_bboxes = []
        for idx in indexes:
            if 0 <= idx < len(primary):
                bbox = primary[idx]
                if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                    x1, y1, x2, y2 = bbox
                    # Skip malformed coordinates
                    if x2 >= x1 and y2 >= y1:
                        selected_bboxes.append(list(bbox))
            # Silently skip invalid indices

        if not selected_bboxes:
            return (json.dumps([{"x": 0, "y": 0}]), [[0, 0, 0, 0]])

        # Image size handling (PIL Image or tensor / ndarray-like)
        img_w = img_h = None
        if hasattr(image, 'size'):
            try:
                # PIL.Image returns (w,h); some objects might return tuple
                img_w, img_h = image.size[0], image.size[1]
            except Exception:
                pass
        if (img_w is None or img_h is None) and hasattr(image, 'shape'):
            shape = getattr(image, 'shape')
            if isinstance(shape, (list, tuple)) and len(shape) >= 3:
                # Assume (B,H,W,C) or (H,W,C)
                if len(shape) == 4:
                    _, img_h, img_w, _ = shape
                else:
                    img_h, img_w = shape[0], shape[1]
        if img_w is None or img_h is None:
            img_w = img_w or 1
            img_h = img_h or 1

        def area(b):
            return max(0, (b[2]-b[0])) * max(0, (b[3]-b[1]))

        chosen = selected_bboxes[0]
        if method == "biggest" and selected_bboxes:
            chosen = max(selected_bboxes, key=area)
        elif method == "center" and selected_bboxes:
            cx_img, cy_img = img_w / 2.0, img_h / 2.0
            def dist2(b):
                cx = (b[0] + b[2]) / 2.0
                cy = (b[1] + b[3]) / 2.0
                return (cx - cx_img) ** 2 + (cy - cy_img) ** 2
            chosen = min(selected_bboxes, key=dist2)
        elif method == "balanced" and selected_bboxes:
            cx_img, cy_img = img_w / 2.0, img_h / 2.0
            def score(b):
                a = area(b) + 1e-5
                cx = (b[0] + b[2]) / 2.0
                cy = (b[1] + b[3]) / 2.0
                d = (cx - cx_img) ** 2 + (cy - cy_img) ** 2
                return d / a
            chosen = min(selected_bboxes, key=score)

        # Compute center of selected bbox (chosen based on method)
        cx = (chosen[0] + chosen[2]) / 2.0
        cy = (chosen[1] + chosen[3]) / 2.0
        center_obj = {"x": int(cx), "y": int(cy)}

        # Return a JSON ARRAY of centers (even if single) to keep datatype consistent with Florence2toCoordinates
        return (json.dumps([center_obj]), [chosen])

class imp_getMaskBoundingBoxNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "mask": ("MASK", {"default": None}),
                "padPct": ("FLOAT", {"default": 0.0, "min": -100.0, "max": 100.0, "step": 0.1, "help": "Optional padding percentage to expand or shrink the bounding box by a pct of the smallest dimension."}),
            },
        }
    
    RETURN_TYPES = ("MASK", "INT", "INT", "INT", "INT")
    RETURN_NAMES =("mask", "xLeft", "yTop", "width", "height")
    FUNCTION = "get_bounding_box"
    CATEGORY = "🐝TinyBee/Util"

    def get_bounding_box(self, mask, padPct=0):
        """Return a PyTorch mask tensor shaped [B, H, W] and bbox ints.

        - Accepts mask as torch.Tensor, numpy.ndarray, or compatible.
        - Computes bbox over union across batch and channels (any pixel > 0).
        - Returns a SOLID rectangular mask: ones inside the bbox, zeros outside.
        - Output conforms to ComfyUI MASK convention: float32 tensor [B, H, W].
        """
        # Normalize to torch tensor
        if mask is None:
            # Return an empty 1x1 mask tensor [B,H,W] to satisfy type/shape
            empty = torch.zeros((1, 1, 1), dtype=torch.float32)
            return (empty, 0, 0, 0, 0)

        if isinstance(mask, torch.Tensor):
            t = mask
        elif isinstance(mask, np.ndarray):
            t = torch.from_numpy(mask)
        else:
            try:
                # Fallback best-effort
                t = torch.tensor(mask)
            except Exception:
                empty = torch.zeros((1, 1, 1), dtype=torch.float32)
                return (empty, 0, 0, 0, 0)

        # Ensure float32 for mask math; keep device
        device = t.device if isinstance(t, torch.Tensor) else "cpu"
        t = t.to(device=device, dtype=torch.float32)

        # Standardize shape to [B, H, W, C]
        # Accept [H, W], [H, W, C], [B, H, W], [B, H, W, C]
        if t.dim() == 2:
            # [H, W] -> [1, H, W, 1]
            t = t.unsqueeze(0).unsqueeze(-1)
        elif t.dim() == 3:
            H, W, D = t.shape if t.shape[-1] in (1, 3, 4) else (None, None, None)
            if D is not None:
                # [H, W, C] -> [1, H, W, C]
                t = t.unsqueeze(0)
            else:
                # [B, H, W] -> [B, H, W, 1]
                t = t.unsqueeze(-1)
        elif t.dim() == 4:
            pass  # already [B, H, W, C]
        else:
            # Unsupported rank; return empty
            empty = torch.zeros((1, 1, 1), dtype=torch.float32, device=device)
            return (empty, 0, 0, 0, 0)

        # Force single channel output (C=1)
        if t.shape[-1] != 1:
            t = t[..., :1]

        B, H, W, _ = t.shape

        # Compute union mask across batch/channel to identify bbox region
        active_any = (t > 0).any(dim=0).any(dim=-1)  # [H, W]

        if not torch.any(active_any):
            zero = torch.zeros((B, H, W), dtype=torch.float32, device=device)
            return (zero, 0, 0, 0, 0)

        ys, xs = torch.where(active_any)
        x_min = int(xs.min().item())
        x_max = int(xs.max().item())
        y_min = int(ys.min().item())
        y_max = int(ys.max().item())

        width = x_max - x_min + 1
        height = y_max - y_min + 1

        # Apply padding if padPct is non-zero
        if padPct != 0:
            # Calculate padding based on smallest dimension
            smallest_dim = min(width, height)
            pad_amount = int(round(smallest_dim * padPct / 100.0))
            
            # Apply uniform padding in all four directions
            x_min -= pad_amount
            y_min -= pad_amount
            width += 2 * pad_amount
            height += 2 * pad_amount
            
            # Clip to image bounds
            if x_min < 0:
                width += x_min  # reduce width by the amount we're clipping
                x_min = 0
            if y_min < 0:
                height += y_min  # reduce height by the amount we're clipping
                y_min = 0
            if x_min + width > W:
                width = W - x_min
            if y_min + height > H:
                height = H - y_min
            
            # Ensure minimum dimensions of 1
            width = max(1, width)
            height = max(1, height)

        # Create a rectangular mask and apply it to all batches
        rect = torch.zeros((H, W), dtype=torch.bool, device=device)
        rect[y_min:y_min + height, x_min:x_min + width] = True
        rect = rect.unsqueeze(0).unsqueeze(-1)  # [1, H, W, 1]

        # Build solid rectangle mask (ones inside bbox, zeros elsewhere) across all batches
        bbox_mask = rect.expand(B, H, W, 1).to(dtype=t.dtype)  # [B, H, W, 1]
        bbox_mask = bbox_mask.squeeze(-1)  # [B, H, W]

        return (bbox_mask, x_min, y_min, width, height)

class imp_faceBodyAspectBoundsNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "face_x": ("INT", {"default": 0, "min": -10000, "max": 10000}),
                "face_y": ("INT", {"default": 0, "min": -10000, "max": 10000}),
                "face_width": ("INT", {"default": 128, "min": 1, "max": 10000}),
                "face_height": ("INT", {"default": 128, "min": 1, "max": 10000}),
                "body_x": ("INT", {"default": 0, "min": -10000, "max": 10000}),
                "body_y": ("INT", {"default": 0, "min": -10000, "max": 10000}),
                "body_width": ("INT", {"default": 256, "min": 1, "max": 10000}),
                "body_height": ("INT", {"default": 512, "min": 1, "max": 10000}),
                "aspect_ratio": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 100.0, "step": 0.01}),
            }
        }

    @staticmethod
    def faceBodyAspectBounds(face_x, face_y, face_width, face_height,
                             body_x, body_y, body_width, body_height,
                             aspect_ratio):
        # We have a body bounding box, and a face bounding box within it.
        # The face box is relative to the body box's x and y (top left corner).
        # We want to adjust the body box to the desired aspect ratio, while ensuring
        # the face box remains fully inside the new body box.
        # We do NOT want to change the body_height, only the width.
        # If we can, we will center the new bounding box around the face box.
        # It is fine if we need to shift the body box's x or grow it's width
        # to ensure the face box fits.
        
        # Calculate the new width based on the desired aspect ratio and body height
        new_width = body_height * aspect_ratio
        
        # Calculate the absolute position of the face box
        abs_face_x = body_x + face_x
        abs_face_right = abs_face_x + face_width
        
        # Calculate the center of the face box
        face_center_x = abs_face_x + (face_width / 2.0)
        
        # Try to center the new body box around the face center
        new_body_x = face_center_x - (new_width / 2.0)
        
        # Ensure the face box is fully contained within the new body box
        # Check if face left edge is inside
        if abs_face_x < new_body_x:
            new_body_x = abs_face_x
        
        # Check if face right edge is inside
        if abs_face_right > (new_body_x + new_width):
            new_body_x = abs_face_right - new_width
        
        # Prevent body_x from going negative (assuming 0 is the left edge of the image)
        if new_body_x < 0:
            new_body_x = 0

        # Calculate the new face bounding box (relative to the new body position)
        # Since face box is relative to body box, we need to adjust face_x based on body_x change
        new_face_x = abs_face_x - new_body_x
        new_face_y = face_y  # y position doesn't change since body_y doesn't change
        
        # Adjust face dimensions to match the aspect ratio
        # Only grow the box, never shrink it - grow in all directions evenly
        new_face_width = face_width
        new_face_height = face_height
        
        # Calculate what the dimensions should be based on aspect ratio
        # Try width-based calculation first
        width_based_height = face_width / aspect_ratio
        # Try height-based calculation
        height_based_width = face_height * aspect_ratio
        
        # Choose the approach that grows (or maintains) the box
        if width_based_height >= face_height:
            # Growing height based on current width satisfies "don't shrink"
            new_face_height = width_based_height
        else:
            # Need to grow width to match aspect ratio without shrinking height
            new_face_width = height_based_width

        # Calculate the amount of growth needed in each dimension
        width_growth = new_face_width - face_width
        height_growth = new_face_height - face_height
        
        # Calculate the absolute position of the current face box
        abs_face_y = body_y + face_y
        abs_face_bottom = abs_face_y + face_height
        
        # Calculate the center of the face box
        face_center_y = abs_face_y + (face_height / 2.0)
        
        # Try to grow evenly in all directions (half growth on each side)
        # For horizontal growth
        left_growth = width_growth / 2.0
        right_growth = width_growth / 2.0
        
        # For vertical growth
        top_growth = height_growth / 2.0
        bottom_growth = height_growth / 2.0
        
        # Check constraints against body box and adjust growth distribution
        # Horizontal constraints
        new_face_left = abs_face_x - left_growth
        new_face_right = abs_face_x + face_width + right_growth
        
        # If we exceed body box on the left, shift growth to the right
        if new_face_left < body_x:
            excess = body_x - new_face_left
            left_growth -= excess
            right_growth += excess
            new_face_left = body_x
            new_face_right = abs_face_x + face_width + right_growth
        
        # If we exceed body box on the right, shift growth to the left
        if new_face_right > (body_x + body_width):
            excess = new_face_right - (body_x + body_width)
            right_growth -= excess
            left_growth += excess
            new_face_right = body_x + body_width
            new_face_left = abs_face_x - left_growth
        
        # Vertical constraints
        new_face_top = abs_face_y - top_growth
        new_face_bottom = abs_face_y + face_height + bottom_growth
        
        # If we exceed body box on the top, shift growth to the bottom
        if new_face_top < body_y:
            excess = body_y - new_face_top
            top_growth -= excess
            bottom_growth += excess
            new_face_top = body_y
            new_face_bottom = abs_face_y + face_height + bottom_growth
        
        # If we exceed body box on the bottom, shift growth to the top
        if new_face_bottom > (body_y + body_height):
            excess = new_face_bottom - (body_y + body_height)
            bottom_growth -= excess
            top_growth += excess
            new_face_bottom = body_y + body_height
            new_face_top = abs_face_y - top_growth
        
        # Calculate final face box position and dimensions
        final_abs_face_x = abs_face_x - left_growth
        final_abs_face_y = abs_face_y - top_growth
        final_face_width = face_width + left_growth + right_growth
        final_face_height = face_height + top_growth + bottom_growth
        
        # Return absolute coordinates for face box (not relative to body box)
        return (int(round(new_body_x)), int(round(body_y)), int(round(new_width)), int(round(body_height)), 
                int(round(final_abs_face_x)), int(round(final_abs_face_y)), int(round(final_face_width)), int(round(final_face_height)))

    RETURN_TYPES = ("INT", "INT", "INT", "INT", "INT", "INT", "INT", "INT")
    RETURN_NAMES = ("body_x", "body_y", "body_width", "body_height", "face_x", "face_y", "face_width", "face_height")
    FUNCTION = "faceBodyAspectBounds"
    CATEGORY = "🐝TinyBee/Util"

CASE_MATCH_TYPES = ["case sensitive", "case insensitive", "match case"]
class imp_searchReplaceNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_string": ("STRING", {"default": "", "multiline": True}),
                "search_string": ("STRING", {"default": "", "forceInput": False}),
                "replace_string": ("STRING", {"default": "", "forceInput": False}),
                "case_sensitive": (CASE_MATCH_TYPES, {"default": CASE_MATCH_TYPES[0], "forceInput": False}),
            }
        }

    @staticmethod
    def searchReplace(input_string, search_string, replace_string, case_sensitive=CASE_MATCH_TYPES[0], match_case=False):
        if not search_string:
            return (input_string,)

        def match_replacement_case(found, replacement):
            if found.islower():
                return replacement.lower()
            elif found.isupper():
                return replacement.upper()
            elif found[0].isupper() and found[1:].islower():
                return replacement.capitalize()
            else:
                return replacement
        
        if case_sensitive == "case insensitive":
            pattern = re.compile(re.escape(search_string), re.IGNORECASE)
            result = pattern.sub(replace_string, input_string)
        elif case_sensitive == "match case":
            def replacer(match):
                found = match.group(0)
                return match_replacement_case(found, replace_string)
            pattern = re.compile(re.escape(search_string), re.IGNORECASE)
            result = pattern.sub(replacer, input_string)
        else:
            result = input_string.replace(search_string, replace_string)

        return (result,)

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output_string",)
    FUNCTION = "searchReplace"
    CATEGORY = "🐝TinyBee/Strings"

class imp_iterateSeedNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "init_seed": ("INT", {"default": 0, "min": -1, "max": 2147483647, "forceInput": True}),
                "method": (["increment", "random"], {"default": "increment", "forceInput": False}),
            }
        }

    @staticmethod
    def iterateSeed(init_seed, method="increment"):
        """Increment the seed by 1, wrapping around if exceeding max int."""
        new_seed = init_seed
        if method == "random":
            random.seed(init_seed)
            new_seed = random.randint(-2147483648, 2147483647)
            return (new_seed,)
        else:  # increment
            if init_seed == -1:
                new_seed = -1
            else:
                new_seed = init_seed + 1
                if new_seed > 2147483647:
                    new_seed = 0
        return (new_seed,)

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("new_seed",)
    FUNCTION = "iterateSeed"
    CATEGORY = "🐝TinyBee/Util"

class imp_autoSeedNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "optional": {
                "reset_seed": ("INT", {"default": -1, "min": -1, "max": 0xffffffffffffffff}),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    @staticmethod
    def autoSeed(reset_seed=-1):
        global _auto_seed_counter
        if reset_seed >= 0:
            _auto_seed_counter = reset_seed
        else:
            _auto_seed_counter += 1
        output = random.Random(_auto_seed_counter).randint(0, 0xffffffffffffffff)
        return (output,)

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("seed",)
    FUNCTION = "autoSeed"
    CATEGORY = "🐝TinyBee/Util"

class imp_intToBoolNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "integer": ("INT", {"default": 0, "min": -2147483648, "max": 2147483647}),
            }
        }

    @staticmethod
    def intToBool(integer):
        """Convert integer to boolean: returns True if non-zero, False if zero."""
        return (integer != 0,)

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("boolean",)
    FUNCTION = "intToBool"
    CATEGORY = "🐝TinyBee/Casting"

class imp_intToLeadingStringNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "integer": ("INT", {"default": 0, "min": -2147483648, "max": 2147483647}),
                "min_digit_count": ("INT", {"default": 1, "min": 1, "max": 20}),
            }
        }

    @staticmethod
    def intToLeadingString(integer, min_digit_count):
        negative = integer < 0
        digits = str(abs(integer)).zfill(min_digit_count)
        return (f"-{digits}" if negative else digits,)

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string",)
    FUNCTION = "intToLeadingString"
    CATEGORY = "🐝TinyBee/Casting"


class imp_stringToIntNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string": ("STRING", {"default": "0"}),
            }
        }

    @staticmethod
    def stringToInt(string):
        """Convert string to integer. Returns 0 if conversion fails."""
        try:
            value = int(string)
        except ValueError:
            value = 0
        return (value,)

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("integer",)
    FUNCTION = "stringToInt"
    CATEGORY = "🐝TinyBee/Casting"

class imp_stringToFloatNode:
    def __init__(self):
        pass

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return _kwargs_digest(kwargs)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string": ("STRING", {"default": "0.0"}),
                "ndigits": ("INT", {"default": -1, "min": -1, "max": 17}),
            }
        }

    @staticmethod
    def stringToFloat(string, ndigits):
        try:
            value = float(string)
        except (ValueError, TypeError):
            value = 0.0
        if ndigits >= 0:
            value = round(value, ndigits)
        return (value,)

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("float",)
    FUNCTION = "stringToFloat"
    CATEGORY = "🐝TinyBee/Casting"

class imp_isStringEmptyNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "str": ("STRING", {"default": "", "min_length": 0, "max_length": 2147483647}),
            },
            "optional": {
                "trim_whitespace": ("BOOLEAN", {"default": True, "label_on": "Trim Whitespace", "label_off": "No Trim"}),
            }
        }

    @staticmethod
    def isStringEmpty(str, trim_whitespace=True):
        """Trim the string of all white space and new line characters."""
        if trim_whitespace:
            str = str.strip()
        return (len(str) == 0,)

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("boolean",)
    FUNCTION = "isStringEmpty"
    CATEGORY = "🐝TinyBee/Strings"


class imp_miniSearchReplaceNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "original": ("STRING", {"default": "", "multiline": False}),
                "search": ("STRING", {"default": "", "multiline": False}),
                "replace": ("STRING", {"default": "", "multiline": False}),
            }
        }

    @staticmethod
    def stringReplace(original, search, replace):
        result = original.replace(search, replace)
        return (result,)

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("result",)
    FUNCTION = "stringReplace"
    CATEGORY = "🐝TinyBee/Strings"


class imp_stringContainsNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string": ("STRING", {"default": ""}),
                "substring": ("STRING", {"default": ""}),
            },
            "optional": {
                "case_sensitive": ("BOOLEAN", {"default": True, "label_on": "Case Sensitive", "label_off": "Case Insensitive"}),
            }
        }

    @staticmethod
    def stringContains(string, substring, case_sensitive=True):
        """Check if the substring is contained within the string."""
        if not case_sensitive:
            string = string.lower()
            substring = substring.lower()
        return (substring in string,)
    
    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("contains",)
    FUNCTION = "stringContains"
    CATEGORY = "🐝TinyBee/Strings"

class imp_sanitizeFilePathNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "path": ("STRING", {"default": ""}),
                "replace_spaces": ("STRING", {"default": " ", "forceInput": False}),
                "replace_invalid_chars": ("STRING", {"default": "_", "forceInput": False}),
                "extra_invalid_chars": ("STRING", {"default": "", "forceInput": False}),
            }
        }

    @staticmethod
    def sanitizeFilePath(path, replace_spaces=" ", replace_invalid_chars="_", extra_invalid_chars=""):
        """Sanitize the file path by removing invalid characters."""
        sanitized_path = re.sub(r'[,<>:"/\\|?*]', replace_invalid_chars, path)
        if replace_spaces != " ":
            sanitized_path = sanitized_path.replace(" ", replace_spaces)
        if extra_invalid_chars:
            sanitized_path = re.sub(f"[{re.escape(extra_invalid_chars)}]", replace_invalid_chars, sanitized_path)
        return (sanitized_path,)

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("sanitized_path",)
    FUNCTION = "sanitizeFilePath"
    CATEGORY = "🐝TinyBee/Strings"


_MAX_COMBINE_LISTS = 10


class imp_stringCombinerNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "num_lists": ("INT", {"default": 2, "min": 1, "max": _MAX_COMBINE_LISTS}),
                "template": ("STRING", {"default": "%1, %2", "multiline": True, "forceInput": False}),
                "index": ("INT", {"default": 0, "min": -1, "max": 2147483647, "forceInput": False}),
            },
            "optional": {},
        }
        for i in range(1, _MAX_COMBINE_LISTS + 1):
            inputs["optional"][f"list_{i}"] = ("STRING", {"forceInput": True})
        return inputs
    
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    @staticmethod
    def combineStrings(num_lists, template, index, **kwargs):
        n = int(num_lists[0]) if isinstance(num_lists, (list, tuple)) else int(num_lists)
        tmpl = str(template[0]) if isinstance(template, (list, tuple)) else str(template)
        idx = int(index[0]) if isinstance(index, (list, tuple)) else int(index)

        lists = []
        for i in range(1, n + 1):
            list_key = f"list_{i}"
            if list_key in kwargs:
                lists.append(kwargs[list_key])
            else:
                lists.append("")

        total_combos = 1
        for lst in lists:
            total_combos *= len(lst) if isinstance(lst, (list, tuple)) else 1

        if idx == -1:
            idx = random.randint(0, total_combos - 1) if total_combos > 0 else 0
        else:
            idx = idx % total_combos if total_combos > 0 else 0

        combination = []
        for lst in reversed(lists):
            if isinstance(lst, (list, tuple)) and len(lst) > 0:
                list_idx = idx % len(lst)
                combination.append(lst[list_idx])
                idx //= len(lst)
            else:
                combination.append("")

        combination.reverse()
        combined_string = tmpl
        for i, value in enumerate(combination, start=1):
            combined_string = combined_string.replace(f"%{i}", str(value))

        return (combined_string, idx, total_combos)


    RETURN_TYPES = ("STRING", "INT", "INT")
    INPUT_IS_LIST = True
    RETURN_NAMES = ("combined_string", "index", "total_combos")
    FUNCTION = "combineStrings"
    CATEGORY = "🐝TinyBee/Strings"

class imp_noneImgConstNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
            }
        }

    @staticmethod
    def noneConst():
        """Return a None constant."""
        return (None,)

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("none",)
    FUNCTION = "noneConst"
    CATEGORY = "🐝TinyBee/Casting"


_COMPARE_OPS = ["GT", "LT", "GTE", "LTE", "EQUAL", "NOTEQUAL"]

def _apply_compare_op(a, b, op):
    if op == "GT":      return a > b
    if op == "LT":      return a < b
    if op == "GTE":     return a >= b
    if op == "LTE":     return a <= b
    if op == "EQUAL":   return a == b
    if op == "NOTEQUAL":return a != b
    return False


class imp_floatCompareNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "a": ("FLOAT", {"default": 0.0}),
                "b": ("FLOAT", {"default": 0.0}),
                "op": (_COMPARE_OPS, {"default": "EQUAL"}),
            }
        }

    @staticmethod
    def compare(a, b, op):
        return (_apply_compare_op(float(a), float(b), op),)

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("Result",)
    FUNCTION = "compare"
    CATEGORY = "🐝TinyBee/Casting"


class imp_intCompareNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "a": ("INT", {"default": 0}),
                "b": ("INT", {"default": 0}),
                "op": (_COMPARE_OPS, {"default": "EQUAL"}),
            }
        }

    @staticmethod
    def compare(a, b, op):
        return (_apply_compare_op(int(a), int(b), op),)

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("Result",)
    FUNCTION = "compare"
    CATEGORY = "🐝TinyBee/Casting"


class imp_stringCompareNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "a": ("STRING", {"default": ""}),
                "b": ("STRING", {"default": ""}),
                "op": (_COMPARE_OPS, {"default": "EQUAL"}),
            }
        }

    @staticmethod
    def compare(a, b, op):
        return (_apply_compare_op(str(a), str(b), op),)

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("Result",)
    FUNCTION = "compare"
    CATEGORY = "🐝TinyBee/Casting"


class imp_floatsToRectNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "nanValue": ("FLOAT", {"default": -1.0}),
            },
            "optional": {
                "x":  ("FLOAT", {"default": -1.0}),
                "y":  ("FLOAT", {"default": -1.0}),
                "w":  ("FLOAT", {"default": -1.0}),
                "h":  ("FLOAT", {"default": -1.0}),
                "x2": ("FLOAT", {"default": -1.0}),
                "y2": ("FLOAT", {"default": -1.0}),
            }
        }

    @staticmethod
    def floatsToRect(nanValue, x=-1.0, y=-1.0, w=-1.0, h=-1.0, x2=-1.0, y2=-1.0):
        nan = float(nanValue)

        def is_set(v):
            return float(v) != nan

        fx  = float(x)  if is_set(x)  else None
        fy  = float(y)  if is_set(y)  else None
        fw  = float(w)  if is_set(w)  else None
        fh  = float(h)  if is_set(h)  else None
        fx2 = float(x2) if is_set(x2) else None
        fy2 = float(y2) if is_set(y2) else None

        # Resolve X and width — priority: use x+w if all three are known
        if fx is not None and fw is not None:
            out_x, out_w = fx, fw
        elif fx is not None and fx2 is not None:
            out_x, out_w = fx, fx2 - fx
        elif fw is not None and fx2 is not None:
            out_x, out_w = fx2 - fw, fw
        else:
            out_x, out_w = 0.0, 0.0

        # Resolve Y and height — priority: use y+h if all three are known
        if fy is not None and fh is not None:
            out_y, out_h = fy, fh
        elif fy is not None and fy2 is not None:
            out_y, out_h = fy, fy2 - fy
        elif fh is not None and fy2 is not None:
            out_y, out_h = fy2 - fh, fh
        else:
            out_y, out_h = 0.0, 0.0

        return ((out_x, out_y, out_w, out_h),)

    RETURN_TYPES = ("TINYRECT",)
    RETURN_NAMES = ("tinyrect",)
    FUNCTION = "floatsToRect"
    CATEGORY = "🐝TinyBee/Casting"


class imp_rectToFloatsNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "tinyrect": ("TINYRECT",),
            }
        }

    @staticmethod
    def rectToFloats(tinyrect):
        x, y, w, h = float(tinyrect[0]), float(tinyrect[1]), float(tinyrect[2]), float(tinyrect[3])
        return (x, y, w, h, x + w, y + h)

    RETURN_TYPES = ("FLOAT", "FLOAT", "FLOAT", "FLOAT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("x", "y", "w", "h", "x2", "y2")
    FUNCTION = "rectToFloats"
    CATEGORY = "🐝TinyBee/Rectangles"


class imp_intsToRectNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "nanValue": ("INT", {"default": -1}),
            },
            "optional": {
                "x":  ("INT", {"default": -1}),
                "y":  ("INT", {"default": -1}),
                "w":  ("INT", {"default": -1}),
                "h":  ("INT", {"default": -1}),
                "x2": ("INT", {"default": -1}),
                "y2": ("INT", {"default": -1}),
            }
        }

    @staticmethod
    def intsToRect(nanValue, x=-1, y=-1, w=-1, h=-1, x2=-1, y2=-1):
        nan = int(nanValue)

        def is_set(v):
            return int(v) != nan

        ix  = float(int(x))  if is_set(x)  else None
        iy  = float(int(y))  if is_set(y)  else None
        iw  = float(int(w))  if is_set(w)  else None
        ih  = float(int(h))  if is_set(h)  else None
        ix2 = float(int(x2)) if is_set(x2) else None
        iy2 = float(int(y2)) if is_set(y2) else None

        # Resolve X and width — priority: use x+w if all three are known
        if ix is not None and iw is not None:
            out_x, out_w = ix, iw
        elif ix is not None and ix2 is not None:
            out_x, out_w = ix, ix2 - ix
        elif iw is not None and ix2 is not None:
            out_x, out_w = ix2 - iw, iw
        else:
            out_x, out_w = 0.0, 0.0

        # Resolve Y and height — priority: use y+h if all three are known
        if iy is not None and ih is not None:
            out_y, out_h = iy, ih
        elif iy is not None and iy2 is not None:
            out_y, out_h = iy, iy2 - iy
        elif ih is not None and iy2 is not None:
            out_y, out_h = iy2 - ih, ih
        else:
            out_y, out_h = 0.0, 0.0

        return ((out_x, out_y, out_w, out_h),)

    RETURN_TYPES = ("TINYRECT",)
    RETURN_NAMES = ("tinyrect",)
    FUNCTION = "intsToRect"
    CATEGORY = "🐝TinyBee/Rectangles"


class imp_rectToIntsNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "tinyrect": ("TINYRECT",),
                "roundFloats": ("BOOLEAN", {"default": False, "label_on": "Round", "label_off": "Truncate"}),
            }
        }

    @staticmethod
    def rectToInts(tinyrect, roundFloats=False):
        x, y, w, h = float(tinyrect[0]), float(tinyrect[1]), float(tinyrect[2]), float(tinyrect[3])
        conv = round if roundFloats else int
        ix, iy, iw, ih = conv(x), conv(y), conv(w), conv(h)
        return (ix, iy, iw, ih, ix + iw, iy + ih)

    RETURN_TYPES = ("INT", "INT", "INT", "INT", "INT", "INT")
    RETURN_NAMES = ("x", "y", "w", "h", "x2", "y2")
    FUNCTION = "rectToInts"
    CATEGORY = "🐝TinyBee/Rectangles"


class imp_intersectRectsNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "rectA": ("TINYRECT",),
                "rectB": ("TINYRECT",),
            }
        }

    @staticmethod
    def intersectRects(rectA, rectB):
        ax, ay, aw, ah = float(rectA[0]), float(rectA[1]), float(rectA[2]), float(rectA[3])
        bx, by, bw, bh = float(rectB[0]), float(rectB[1]), float(rectB[2]), float(rectB[3])
        ix = max(ax, bx)
        iy = max(ay, by)
        ix2 = min(ax + aw, bx + bw)
        iy2 = min(ay + ah, by + bh)
        return ((ix, iy, ix2 - ix, iy2 - iy),)

    RETURN_TYPES = ("TINYRECT",)
    RETURN_NAMES = ("tinyrect",)
    FUNCTION = "intersectRects"
    CATEGORY = "🐝TinyBee/Rectangles"


class imp_rectFromImgNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            }
        }

    @staticmethod
    def rectFromImg(image):
        batch = _normalize_image_batch(image)
        h = float(batch.shape[1])
        w = float(batch.shape[2])
        return ((0.0, 0.0, w, h),)

    RETURN_TYPES = ("TINYRECT",)
    RETURN_NAMES = ("tinyrect",)
    FUNCTION = "rectFromImg"
    CATEGORY = "🐝TinyBee/Rectangles"


class imp_scaleRectNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "tinyrect": ("TINYRECT",),
                "xScale": ("FLOAT", {"default": 1.0, "step": 0.01}),
                "yScale": ("FLOAT", {"default": 1.0, "step": 0.01}),
            }
        }

    @staticmethod
    def scaleRect(tinyrect, xScale, yScale):
        x, y, w, h = float(tinyrect[0]), float(tinyrect[1]), float(tinyrect[2]), float(tinyrect[3])
        return ((x * float(xScale), y * float(yScale), w * float(xScale), h * float(yScale)),)

    RETURN_TYPES = ("TINYRECT",)
    RETURN_NAMES = ("tinyrect",)
    FUNCTION = "scaleRect"
    CATEGORY = "🐝TinyBee/Rectangles"


class imp_sequenceNode:
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # Using unique lowercase/uppercase patterns or standard types helps ComfyUI resolve the inputs
                "passthrough": ("STRING", {"forceInput": True}),
                "dependency": ("STRING", {"forceInput": True}),
            }
        }

    @staticmethod
    def sequence(passthrough, dependency):
        return (passthrough,)

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("passthrough",)
    FUNCTION = "sequence"
    CATEGORY = "🐝TinyBee/Util"

class imp_interpolateFramesNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "frame_count": ("INT", {"default": 10, "min": 0, "max": 1000}),
                "include_begin": ("BOOLEAN", {"default": True, "label_on": "Include Begin", "label_off": "Exclude Begin"}),
                "include_end": ("BOOLEAN", {"default": True, "label_on": "Include End", "label_off": "Exclude End"}),
            },
            "optional": {
                "begin_image": ("IMAGE", {"default": None}),
                "end_image": ("IMAGE", {"default": None}),
            }
        }

    @staticmethod
    def interpolateFrames(frame_count, include_begin, include_end, begin_image=None, end_image=None):
        """
        Interpolate frames between two images.
        
        Args:
            frame_count: Number of interpolated frames (not including begin/end)
            include_begin: Whether to include the beginning image
            include_end: Whether to include the ending image
            begin_image: Starting image (optional)
            end_image: Ending image (optional)
        
        Returns:
            A batch of interpolated frames as a torch tensor
        """
        # Validate that at least one image is provided
        if begin_image is None and end_image is None:
            raise ValueError("At least one image (begin_image or end_image) must be provided")
        
        # Normalize images to torch tensors
        def normalize_image(img):
            if img is None:
                return None
            if isinstance(img, np.ndarray):
                return torch.from_numpy(img)
            elif isinstance(img, torch.Tensor):
                return img
            elif isinstance(img, list):
                return torch.stack([torch.tensor(i) if not isinstance(i, torch.Tensor) else i for i in img])
            else:
                return torch.tensor(img)
        
        begin_tensor = normalize_image(begin_image)
        end_tensor = normalize_image(end_image)
        
        # If begin_tensor is a batch, use only the first image
        if begin_tensor is not None and begin_tensor.dim() == 4:
            begin_tensor = begin_tensor[0]
        
        # If end_tensor is a batch, use only the first image
        if end_tensor is not None and end_tensor.dim() == 4:
            end_tensor = end_tensor[0]
        
        # Determine image dimensions
        if begin_tensor is not None:
            height, width, channels = begin_tensor.shape
            device = begin_tensor.device
            dtype = begin_tensor.dtype
        else:
            height, width, channels = end_tensor.shape
            device = end_tensor.device
            dtype = end_tensor.dtype
        
        # Create black images for missing begin/end
        if begin_tensor is None:
            begin_tensor = torch.zeros((height, width, channels), dtype=dtype, device=device)
        
        if end_tensor is None:
            end_tensor = torch.zeros((height, width, channels), dtype=dtype, device=device)
        
        # Ensure both images have the same dimensions
        if begin_tensor.shape != end_tensor.shape:
            raise ValueError(f"Image dimensions must match. Begin: {begin_tensor.shape}, End: {end_tensor.shape}")
        
        # Build the frame list
        frames = []
        
        # Add begin image if requested
        if include_begin:
            frames.append(begin_tensor)
        
        # Generate interpolated frames
        if frame_count > 0:
            for i in range(1, frame_count + 1):
                # Calculate interpolation factor (0 to 1)
                alpha = i / (frame_count + 1)
                
                # Linear interpolation between begin and end
                interpolated = (1 - alpha) * begin_tensor + alpha * end_tensor
                frames.append(interpolated)
        
        # Add end image if requested
        if include_end:
            frames.append(end_tensor)
        
        # If no frames to return, return at least the begin image
        if len(frames) == 0:
            frames.append(begin_tensor)
        
        # Stack frames into a batch
        frame_batch = torch.stack(frames)
        
        return (frame_batch,)

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("frames",)
    FUNCTION = "interpolateFrames"
    CATEGORY = "🐝TinyBee/Video"

# ===========================================================================





# QUEUE MANAGEMENT





# ===========================================================================

PROPVALUETYPES = ["STRING", "INT", "FLOAT", "BOOLEAN", "OBJECT", "LIST", "JSON", "NULL", "UNKNOWN"]
def describeType(value):
    if isinstance(value, str):
        # Determine if the string is valid JSON
        try:
            json.loads(value)
            return "JSON"
        except json.JSONDecodeError:
            return "STRING"
    elif isinstance(value, int):
        return "INT"
    elif isinstance(value, float):
        return "FLOAT"
    elif isinstance(value, bool):
        return "BOOLEAN"
    elif isinstance(value, list):
        return "LIST"
    elif isinstance(value, dict):
        return "OBJECT"
    elif value is None:
        return "NULL"
    else:
        return "UNKNOWN"

# Stores the property as a raw JSON string rather than a dict or list.
def encodeRawJsonProperty(property_name, property_value):
    propObj = encodeRawProperty(property_name, property_value)
    propObj["type"] = "JSON"
    propObj["value"] = json.dumps(property_value)    
    return propObj

def encodeRawProperty(property_name, property_value, value_type="UNKNOWN"):
        # Encode a name/value pair as a JSON property string.
        if value_type == "JSON":
            return encodeRawJsonProperty(property_name, property_value)
        
        if value_type == "UNKNOWN":
            value_type = describeType(property_value)
        elif value_type == "NULL":
            property_value = None

        propObj = {
            "name": property_name,
            "type": value_type,
            "value": property_value
        }
        return propObj


class imp_encodeAnyPropertyNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "property_name": ("STRING", {"default": "property"}),
                "property_value": (generic_type,),  
                "property_type": (PROPVALUETYPES, {"default": "UNKNOWN", "forceInput": False}),
            }
        }

    @staticmethod
    def encodeAnyProperty(property_name, property_value, property_type):
        return (encodeRawProperty(property_name, property_value, property_type),)
        
    RETURN_TYPES = ("TINYPROP",)
    RETURN_NAMES = ("property",)
    FUNCTION = "encodeAnyProperty"
    CATEGORY = "🐝TinyBee/Queue"

class imp_combinePropertiesNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "optional": {
                "prop_a": ("TINYPROP", {"default": None, "ForceInput": True}),
                "prop_b": ("TINYPROP", {"default": None, "ForceInput": True}),
                "prop_c": ("TINYPROP", {"default": None, "ForceInput": True}),
                "prop_d": ("TINYPROP", {"default": None, "ForceInput": True}),
                "existing_properties": ("TINYPROPS", {"default": {}, "ForceInput": True}),
                "override_existing": ("BOOLEAN", {"default": True, "label_on": "Override Existing", "label_off": "Preserve Existing"}),
            }
        }

    @staticmethod
    def combineProperties(prop_a=None, prop_b=None, prop_c=None, prop_d=None, existing_properties=None, override_existing=True):
        """Combine multiple JSON-encoded properties into a single JSON dictionary."""
        combined = {}

        # Load existing properties if valid
        if existing_properties:
            existing_dict = existing_properties
            if isinstance(existing_dict, dict):
                combined.update(existing_dict)

        # Helper to add property if valid
        def add_property(prop):
            if prop:
                if isinstance(prop, dict) and "name" in prop and "value" in prop:
                    if override_existing or prop["name"] not in combined:
                        combined[prop["name"]] = prop

        # Add each property
        add_property(prop_a)
        add_property(prop_b)
        add_property(prop_c)
        add_property(prop_d)

        combined_json = json.dumps(combined)
        return (combined, combined_json)

    RETURN_TYPES = ("TINYPROPS","STRING")
    RETURN_NAMES = ("combined_properties", "combined_properties_json")
    FUNCTION = "combineProperties"
    CATEGORY = "🐝TinyBee/Util"

class imp_getPropertyFromPropertiesNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "properties": ("TINYPROPS", {"default": {}, "ForceInput": True}),
                "property_name": ("STRING", {"default": "property"}),
            }
        }

    @staticmethod
    def getValueFromProperties(properties, property_name):
        """Retrieve a property value by name from a JSON-encoded properties dictionary."""
        props_dict = properties
        if isinstance(props_dict, dict) and property_name in props_dict:
            return (props_dict[property_name], props_dict[property_name].get("value", ""), props_dict[property_name].get("type", "UNKNOWN"))
        return (None, "", "NULL")

    RETURN_TYPES = ("TINYPROP", generic_type, "STRING")
    RETURN_NAMES = ("property", "value", "value_type")
    FUNCTION = "getValueFromProperties"
    CATEGORY = "🐝TinyBee/Util"


class imp_getJsonFromPropertiesNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "properties": ("TINYPROPS", {"default": {}, "ForceInput": True}),
            }
        }

    @staticmethod
    def getJsonFromProperties(properties):
        """Retrieve the entire properties dictionary as a JSON string."""
        if isinstance(properties, dict):
            return (json.dumps(properties),)
        print("imp_getJsonFromPropertiesNode: Invalid properties input; returning empty JSON.")
        return ("{}",)

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("properties_json",)
    FUNCTION = "getJsonFromProperties"
    CATEGORY = "🐝TinyBee/Queue"

class imp_saveImageBatchToZipNode:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_batch": ("IMAGE", {"forceInput": True}),
                "filename_prefix": ("STRING", {"default": "batch", "forceInput": False}),
                "compress_to_zip": ("BOOLEAN", {"default": True, "label_on": "Compress to Zip", "label_off": "Export as Folder"}), 
            },
            "optional": {
                "json_filename": ("STRING", {"default": "metadata.json", "forceInput": False}),
                "json": ("STRING", {"default": "", "multiline": True, "forceInput": False}),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # This node has file-system side effects and should always run when queued.
        return float("NaN")
    
    def saveImageBatchToZip(self, image_batch, filename_prefix, compress_to_zip=True, json_filename="", json=""):
        if image_batch is None or len(image_batch) == 0:
            return ()

        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir)
        
        # Convert to torch tensor if not already
        if isinstance(image_batch, np.ndarray):
            image_batch = torch.from_numpy(image_batch)
        elif not isinstance(image_batch, torch.Tensor):
            # If it's a list, stack into tensor
            if isinstance(image_batch, list):
                image_batch = torch.stack([torch.tensor(img) if not isinstance(img, torch.Tensor) else img for img in image_batch])
            else:
                image_batch = torch.tensor(image_batch)
        
        
        # Create zip file
        if compress_to_zip:
            filename = f"{filename_prefix}.zip"
            with zipfile.ZipFile(os.path.join(full_output_folder, filename), 'w') as zipf:
                # Save each image in the batch
                for i in range(image_batch.shape[0]):
                    img_tensor = image_batch[i]
                    img_array = img_tensor.cpu().numpy()
                    img = Image.fromarray((img_array * 255).astype(np.uint8))
                    img_bytes = BytesIO()
                    img.save(img_bytes, format='PNG')
                    img_bytes.seek(0)
                    zipf.writestr(f'image_{i:04d}.png', img_bytes.read())

                # Optionally add JSON metadata
                if json_filename and json:
                    zipf.writestr(json_filename, json)
        else:
            # Save images to folder
            subpath = os.path.join(full_output_folder, filename)
            os.makedirs(subpath, exist_ok=True)
            for i in range(image_batch.shape[0]):
                img_tensor = image_batch[i]
                img_array = img_tensor.cpu().numpy()
                img = Image.fromarray((img_array * 255).astype(np.uint8))
                img.save(os.path.join(subpath, f'image_{i:04d}.png'))

            # Optionally save JSON metadata
            if json_filename and json:
                with open(os.path.join(subpath, json_filename), 'w') as json_file:
                    json_file.write(json)

        return ()

    RETURN_TYPES = ()
    FUNCTION = "saveImageBatchToZip"
    OUTPUT_NODE = True
    CATEGORY = "🐝TinyBee/Queue"


class imp_saveImageWithMetaNode:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images":           ("IMAGE",),
                "prefix":           ("STRING",  {"default": "ComfyUI", "multiline": False}),
                "prefix_delimiter": ("STRING",  {"default": "_",       "multiline": False}),
                "prefix_2":         ("STRING",  {"default": "",        "multiline": False}),
                "output_folder":    ("STRING",  {"default": "",        "multiline": False}),
                "save_workspace":   ("BOOLEAN", {"default": True,
                                                 "label_on": "Save Workspace",
                                                 "label_off": "No Workspace"}),
            },
            "optional": {
                "metadata_props": ("TINYPROPS", {"default": None}),
            },
            "hidden": {
                "prompt":        "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def save_image_with_meta(self, images, prefix="ComfyUI", prefix_delimiter="_",
                             prefix_2="", output_folder="", save_workspace=True,
                             metadata_props=None, prompt=None, extra_pnginfo=None):
        full_prefix = prefix + (prefix_delimiter + prefix_2 if prefix_2.strip() else "")
        if output_folder.strip():
            full_prefix = output_folder.strip() + "/" + full_prefix

        full_output_folder, filename, counter, subfolder, filename_prefix = \
            folder_paths.get_save_image_path(full_prefix, self.output_dir,
                                             images[0].shape[1], images[0].shape[0])

        results = []
        for batch_number, image in enumerate(images):
            img = Image.fromarray(np.clip(255. * image.cpu().numpy(), 0, 255).astype(np.uint8))

            pnginfo = None
            if not args.disable_metadata:
                pnginfo = PngInfo()
                if prompt is not None:
                    pnginfo.add_text("prompt", json.dumps(prompt))
                if save_workspace and extra_pnginfo is not None:
                    for key in extra_pnginfo:
                        pnginfo.add_text(key, json.dumps(extra_pnginfo[key]))
                if metadata_props:
                    tinyprops_data = {k: {"type": v["type"], "value": v["value"]}
                                      for k, v in metadata_props.items()}
                    pnginfo.add_text("tinyprops", json.dumps(tinyprops_data))

            filename_with_batch = filename.replace("%batch_num%", str(batch_number))
            cleanfile = filename_with_batch + ".png"
            if len(images) == 1 and not os.path.exists(os.path.join(full_output_folder, cleanfile)):
                file = cleanfile
            else:
                file = f"{filename_with_batch}_{counter:05}.png"
            img.save(os.path.join(full_output_folder, file),
                     pnginfo=pnginfo, compress_level=self.compress_level)
            results.append({"filename": file, "subfolder": subfolder, "type": self.type})
            counter += 1

        return {"ui": {"images": results}, "result": (images,)}

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "save_image_with_meta"
    OUTPUT_NODE = True
    CATEGORY = "🐝TinyBee/Images"


class imp_loadImageWithMetaNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_path": ("STRING", {"default": "", "multiline": False}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "TINYPROPS")
    RETURN_NAMES = ("image", "mask", "metadata_props")
    FUNCTION = "load_image_with_meta"
    CATEGORY = "🐝TinyBee/Images"

    def load_image_with_meta(self, image_path):
        resolved = (image_path if os.path.isabs(image_path)
                    else os.path.join(folder_paths.get_output_directory(), image_path))

        img = Image.open(resolved)

        tinyprops = {}
        if hasattr(img, 'text') and 'tinyprops' in img.text:
            try:
                stored = json.loads(img.text['tinyprops'])
                tinyprops = {
                    name: {"name": name, "type": entry["type"], "value": entry["value"]}
                    for name, entry in stored.items()
                }
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        img_rgb = img.convert("RGB")
        img_np = np.array(img_rgb).astype(np.float32) / 255.0
        image_tensor = torch.from_numpy(img_np)[None,]

        if 'A' in img.getbands():
            alpha_np = np.array(img.getchannel('A')).astype(np.float32) / 255.0
            mask_tensor = torch.from_numpy(1. - alpha_np).unsqueeze(0)
        else:
            mask_tensor = torch.zeros(
                (1, image_tensor.shape[1], image_tensor.shape[2]), dtype=torch.float32
            )

        return (image_tensor, mask_tensor, tinyprops)

    @classmethod
    def IS_CHANGED(cls, image_path):
        resolved = (image_path if os.path.isabs(image_path)
                    else os.path.join(folder_paths.get_output_directory(), image_path))
        if not os.path.exists(resolved):
            return float("NaN")
        m = hashlib.sha256()
        with open(resolved, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(cls, image_path):
        if not image_path or not image_path.strip():
            return "Image path cannot be empty"
        resolved = (image_path if os.path.isabs(image_path)
                    else os.path.join(folder_paths.get_output_directory(), image_path))
        if not os.path.exists(resolved):
            return f"Image file not found: {resolved}"
        return True


_MAX_ENCODE_PROPS = 16

class imp_encodeAnyPropertiesNode:
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "num_properties": ("INT", {"default": 3, "min": 1, "max": _MAX_ENCODE_PROPS}),
            },
            "optional": {},
        }
        for i in range(1, _MAX_ENCODE_PROPS + 1):
            inputs["optional"][f"name_{i}"] = ("STRING", {"default": f"property_{i}", "multiline": False})
            inputs["optional"][f"value_{i}"] = (generic_type,)
        return inputs

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def encodeAnyProperties(self, num_properties, **kwargs):
        result = {}
        for i in range(1, num_properties + 1):
            name = kwargs.get(f"name_{i}", f"property_{i}")
            if isinstance(name, str):
                name = name.strip()
            if not name:
                continue
            value = kwargs.get(f"value_{i}")
            result[name] = encodeRawProperty(name, value)
        return (result,)

    RETURN_TYPES = ("TINYPROPS",)
    RETURN_NAMES = ("properties",)
    FUNCTION = "encodeAnyProperties"
    CATEGORY = "🐝TinyBee/Util"


class imp_loadImageBatchFromZipNode:
    def __init__(self):
        pass
        
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "filename": ("STRING", {"default": "input.zip", "forceInput": False}),
                "loadFromFolder": ("BOOLEAN", {"default": False, "label_on": "Load from Folder", "label_off": "Load from Zip"}),
            }
        }
    
    @staticmethod
    def loadImageBatchFromZip(filename, loadFromFolder=False):
        """
        Load images and JSON metadata from a zip file or folder.
        Returns a batch of images as a torch tensor and JSON string.
        """
        images = []
        json_data = "{}"
        
        # Validate that the resolved path stays within the output directory
        output_dir = os.path.abspath(folder_paths.get_output_directory())
        filepath = os.path.abspath(os.path.join(output_dir, filename))
        
        # Security check: ensure filepath is within output_dir
        if not filepath.startswith(output_dir + os.sep) and filepath != output_dir:
            raise ValueError(f"Invalid filename: path traversal detected. Path must be within output directory.")

        # Determine the source path - prefer upload if provided
        source_path = filepath
        if loadFromFolder:
            # Load from folder
            if not os.path.exists(source_path) or not os.path.isdir(source_path):
                print(f"imp_loadImageBatchFromZipNode: Folder not found: {source_path}")
                return (torch.zeros((1, 64, 64, 3), dtype=torch.float32), json_data)
            
            # Find all image files
            image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp']
            image_files = []
            for filename in os.listdir(source_path):
                if any(filename.lower().endswith(ext) for ext in image_extensions):
                    image_files.append(os.path.join(source_path, filename))
            
            # Sort files by name
            image_files.sort()
            
            # Load images
            for img_path in image_files:
                try:
                    img = Image.open(img_path).convert('RGB')
                    img_array = np.array(img).astype(np.float32) / 255.0
                    images.append(torch.from_numpy(img_array))
                except Exception as e:
                    print(f"imp_loadImageBatchFromZipNode: Error loading image {img_path}: {e}")
            
            # Look for JSON file (first .json file found)
            for filename in os.listdir(source_path):
                if filename.lower().endswith('.json'):
                    json_path = os.path.join(source_path, filename)
                    try:
                        with open(json_path, 'r') as f:
                            json_data = f.read()
                        break  # Use first JSON file found
                    except Exception as e:
                        print(f"imp_loadImageBatchFromZipNode: Error reading JSON {json_path}: {e}")
        
        else:
            # Load from zip file
            if not os.path.exists(source_path):
                print(f"imp_loadImageBatchFromZipNode: Zip file not found: {source_path}")
                return (torch.zeros((1, 64, 64, 3), dtype=torch.float32), json_data)
            
            try:
                with zipfile.ZipFile(source_path, 'r') as zipf:
                    # Get list of files in zip
                    file_list = zipf.namelist()
                    
                    # Find and sort image files
                    image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp']
                    image_files = [f for f in file_list if any(f.lower().endswith(ext) for ext in image_extensions)]
                    image_files.sort()
                    
                    # Load images
                    for img_name in image_files:
                        try:
                            with zipf.open(img_name) as img_file:
                                img = Image.open(img_file).convert('RGB')
                                img_array = np.array(img).astype(np.float32) / 255.0
                                images.append(torch.from_numpy(img_array))
                        except Exception as e:
                            print(f"imp_loadImageBatchFromZipNode: Error loading image {img_name} from zip: {e}")
                    
                    # Look for JSON file (first .json file found)
                    json_files = [f for f in file_list if f.lower().endswith('.json')]
                    if json_files:
                        try:
                            with zipf.open(json_files[0]) as json_file:
                                json_data = json_file.read().decode('utf-8')
                        except Exception as e:
                            print(f"imp_loadImageBatchFromZipNode: Error reading JSON from zip: {e}")
            
            except Exception as e:
                print(f"imp_loadImageBatchFromZipNode: Error opening zip file {source_path}: {e}")
                return (torch.zeros((1, 64, 64, 3), dtype=torch.float32), json_data)
        
        # If no images were loaded, return a dummy image
        if not images:
            print("imp_loadImageBatchFromZipNode: No images found")
            return (torch.zeros((1, 64, 64, 3), dtype=torch.float32), json_data)
        
        # Stack images into a batch tensor
        image_batch = torch.stack(images)
        
        return (image_batch, json_data)

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image_batch", "json")
    FUNCTION = "loadImageBatchFromZip"
    CATEGORY = "🐝TinyBee/Queue"

# ===========================================================================





# NODE EXPORTS





# ===========================================================================

class imp_fileMetadataNode:
    def __init__(self):
        pass

    @classmethod
    def IS_CHANGED(cls, image_path=""):
        image_path = (image_path or "").strip()
        if not image_path:
            return ""
        image_dir = os.path.dirname(image_path)
        image_basename = os.path.splitext(os.path.basename(image_path))[0]
        folder_name = os.path.basename(image_dir)
        mtimes = [image_path]
        for path in [
            os.path.join(image_dir, f"{folder_name}-defaults.json"),
            os.path.join(image_dir, f"{image_basename}-meta.json"),
        ]:
            mtimes.append(os.path.getmtime(path) if os.path.isfile(path) else None)
        return str(mtimes)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_path": ("STRING", {"default": "", "forceInput": False}),
            }
        }

    @staticmethod
    def getFileMetadata(image_path=""):
        result = {}

        if not image_path or not image_path.strip():
            return (result,)

        image_dir = os.path.dirname(image_path.strip())
        image_basename = os.path.splitext(os.path.basename(image_path.strip()))[0]
        folder_name = os.path.basename(image_dir)

        # Load folder defaults first (lower priority)
        defaults_path = os.path.join(image_dir, f"{folder_name}-defaults.json")
        if os.path.isfile(defaults_path):
            try:
                with open(defaults_path, "r", encoding="utf-8") as f:
                    defaults_data = json.load(f)
                if isinstance(defaults_data, dict):
                    result.update(defaults_data)
            except Exception as e:
                print(f"[File Metadata] Error reading defaults file {defaults_path}: {e}")

        # Load image meta file second (takes precedence over defaults)
        meta_path = os.path.join(image_dir, f"{image_basename}-meta.json")
        if os.path.isfile(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
                if isinstance(meta_data, dict):
                    result.update(meta_data)
            except Exception as e:
                print(f"[File Metadata] Error reading meta file {meta_path}: {e}")

        return (result,)

    RETURN_TYPES = ("OBJECT",)
    RETURN_NAMES = ("metadata",)
    OUTPUT_IS_LIST = (False,)
    FUNCTION = "getFileMetadata"
    CATEGORY = "🐝TinyBee/Dictionaries"


class imp_jsonParserNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json": ("STRING", {"default": "", "multiline": True, "forceInput": False}),
                "jsonata": ("STRING", {"default": "$", "multiline": False, "forceInput": False}),
                "stripQuotes": ("BOOLEAN", {"default": True, "label_on": "Strip Quotes", "label_off": "Keep Quotes"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
            }
        }

    @staticmethod
    def parseJson(json, jsonata, stripQuotes, seed):
        if _Jsonata is None:
            raise RuntimeError("jsonata is not installed. Run: pip install jsonata")

        raw = _unwrap_single_value(json) or ""
        expr_str = _unwrap_single_value(jsonata) or "$"
        seed_val = int(_unwrap_single_value(seed) or 0)

        try:
            data = json_lib.loads(raw)
        except Exception as e:
            raise ValueError(f"JSON parse error: {e}") from e

        try:
            rng = random.Random(seed_val)

            def _sshuffle(arr):
                if not isinstance(arr, list):
                    return arr
                result = arr[:]
                rng.shuffle(result)
                return result

            expr = _Jsonata(expr_str)
            expr.register_lambda("srnd", rng.random)
            expr.register_lambda("sshuffle", _sshuffle)
            result = expr.evaluate(data)
        except Exception as e:
            raise ValueError(f"JSONata error: {e}") from e

        json_result = json_lib.dumps(result, ensure_ascii=False)

        if stripQuotes:
            json_result = _strip_quotes(json_result)
    
        return (json_result,)

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("result",)
    FUNCTION = "parseJson"
    CATEGORY = "🐝TinyBee/Strings"


class imp_stripQuotesNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"default": "", "forceInput": False, "multiline": False}),
            }
        }

    @staticmethod
    def stripQuotes(text):
        return (_strip_quotes(text),)

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "stripQuotes"
    CATEGORY = "🐝TinyBee/Strings"


class imp_tokenReplaceNode:
    MAX_TOKENS = 10

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        optional_inputs = {}
        for i in range(1, cls.MAX_TOKENS):
            optional_inputs[f"input_{i}"] = ("STRING", {"forceInput": True})
        return {
            "required": {
                "template": ("STRING", {"default": "this will replace %0 with input_0", "multiline": True}),
                "token_count": ("INT", {"default": 1, "min": 1, "max": cls.MAX_TOKENS}),
                "input_0": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": optional_inputs,
        }

    @staticmethod
    def tokenReplace(template, input_0, **kwargs):
        # token_count lands in kwargs; used only by the JS UI to show/hide inputs
        result = str(template)
        result = result.replace("%0", str(input_0))
        for i in range(1, 10):
            value = kwargs.get(f"input_{i}", "") or ""
            result = result.replace(f"%{i}", str(value))
        return (result,)

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("result",)
    FUNCTION = "tokenReplace"
    CATEGORY = "🐝TinyBee/Strings"


# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
    # List Nodes
    "CSV Parser": imp_csvParserNode,
    "Combine Lists": imp_combineListsNode,
    "Decorate List": imp_decorateListNode,
    "Filter Existing Files": imp_filterFileExistsListNode,
    "Filter List": imp_filterListNode,
    "Filter Words": imp_filterWordsNode,
    "Get File List": imp_getFileListNode,
    "Get List From File": imp_getListFromFileNode,
    "Indexed Entry": imp_indexedListEntryNode,
    "List Count": imp_listCountNode,
    "Random Entry": imp_randomListEntryNode,
    "Random File Entry": imp_randomFileEntryNode,
    "Randomize List": imp_randomizeListNode,
    "Replace List": imp_replaceListNode,
    "Sort List": imp_sortListNode,
    "Split List": imp_splitListNode,
    "String To List": imp_stringToListNode,

    # Dictionary Nodes
    "File Metadata": imp_fileMetadataNode,
    "Dictionary Lookup": imp_dictionaryLookupNode,

    # Utility Nodes
    "Process Path Name": imp_processPathNameNode,
    "Incrementer": imp_incrementerNode,
    "Prompt Splitter": imp_promptSplitterNode,
    "Prompt Splitter (Dynamic)": imp_promptSplitterDynamicNode,
    "Timestamp": imp_timestampNode,
    "Tiny Random": imp_tinyRandomNode,
    "Force Aspect On Bounds": imp_forceAspectOnBoundsNode,
    "Sequence": imp_sequenceNode,
    "Select Bounding Box": imp_selectBoundingBoxNode,
    "Get Mask Bounding Box": imp_getMaskBoundingBoxNode,
    "Face Body Aspect Bounds": imp_faceBodyAspectBoundsNode,
    "Iterate Seed": imp_iterateSeedNode,
    "Auto Seed": imp_autoSeedNode,

    # String Nodes
    "JSON Parser": imp_jsonParserNode,
    "Strip Quotes": imp_stripQuotesNode,
    "Token Replace": imp_tokenReplaceNode,
    "Search and Replace": imp_searchReplaceNode,
    "S&R": imp_miniSearchReplaceNode,
    "Search To Boolean": imp_stringContainsNode,
    "Is String Empty": imp_isStringEmptyNode,
    "Sanitize File Path": imp_sanitizeFilePathNode,
    "String Combiner": imp_stringCombinerNode,

    # Casting Nodes
    "Int to Boolean": imp_intToBoolNode,
    "Int to Leading String": imp_intToLeadingStringNode,
    "String to Int": imp_stringToIntNode,
    "String to Float": imp_stringToFloatNode,
    "None Image": imp_noneImgConstNode,
    "Float Compare": imp_floatCompareNode,
    "Int Compare": imp_intCompareNode,
    "String Compare": imp_stringCompareNode,

    # Rectangle Nodes
    "Rect to Floats": imp_rectToFloatsNode,
    "Floats to Rect": imp_floatsToRectNode,
    "Rect to Ints": imp_rectToIntsNode,
    "Ints to Rect": imp_intsToRectNode,
    "Intersect Rects": imp_intersectRectsNode,
    "Rect From Image": imp_rectFromImgNode,
    "Scale Rect": imp_scaleRectNode,

    # Workflow Nodes
    "Grid Maker (Dynamic)": imp_gridMakerDynamicNode,
    "Grid Divider": imp_gridDividerNode,
    "Randomize Image Batch": imp_randomizeImageBatchNode,
    "Images From Batch": imp_imagesFromBatchNode,
    "Save Image Batch to Zip": imp_saveImageBatchToZipNode,
    "Save Image w/Meta": imp_saveImageWithMetaNode,
    "Load Image w/Meta": imp_loadImageWithMetaNode,
    "Load Image Batch from Zip": imp_loadImageBatchFromZipNode,
    "Encode Any Property": imp_encodeAnyPropertyNode,
    "Encode Any Properties (Dynamic)": imp_encodeAnyPropertiesNode,
    "Combine Properties": imp_combinePropertiesNode,
    "Prop From Properties": imp_getPropertyFromPropertiesNode,
    "Json From Properties": imp_getJsonFromPropertiesNode,

    "Interpolate Frames": imp_interpolateFramesNode,
}


def _unwrap_single_value(value):
    if isinstance(value, (list, tuple)) and len(value) == 1:
        return value[0]
    return value


def _to_stable_data(value):
    value = _unwrap_single_value(value)

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    if isinstance(value, dict):
        return {str(k): _to_stable_data(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}

    if isinstance(value, (list, tuple)):
        return [_to_stable_data(v) for v in value]

    if isinstance(value, set):
        return sorted([_to_stable_data(v) for v in value], key=lambda x: json.dumps(x, sort_keys=True, default=str))

    if isinstance(value, torch.Tensor):
        try:
            tensor_cpu = value.detach().to(device="cpu").contiguous()
            content_hash = hashlib.sha256(tensor_cpu.numpy().tobytes()).hexdigest()
        except Exception:
            # Conservative fallback: include repr so failures still differentiate values.
            content_hash = repr(value)

        return {
            "__type__": "torch.Tensor",
            "shape": list(value.shape),
            "dtype": str(value.dtype),
            "device": str(value.device),
            "content_hash": content_hash,
        }

    if isinstance(value, np.ndarray):
        try:
            arr = np.ascontiguousarray(value)
            content_hash = hashlib.sha256(arr.tobytes()).hexdigest()
        except Exception:
            content_hash = repr(value)

        return {
            "__type__": "np.ndarray",
            "shape": list(value.shape),
            "dtype": str(value.dtype),
            "content_hash": content_hash,
        }

    return repr(value)


def _kwargs_digest(kwargs):
    payload = _to_stable_data(kwargs)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _default_is_changed(cls, **kwargs):
    # Default cache key based on normalized input values.
    return _kwargs_digest(kwargs)


for _node_cls in NODE_CLASS_MAPPINGS.values():
    if "IS_CHANGED" not in _node_cls.__dict__:
        _node_cls.IS_CHANGED = classmethod(_default_is_changed)

# Auto-generate display name mappings from NODE_CLASS_MAPPINGS
# Maps class name (e.g., "imp_combineListsNode") to display name (e.g., "Combine Lists")
NODE_DISPLAY_NAME_MAPPINGS = {
    cls.__name__: display_name 
    for display_name, cls in NODE_CLASS_MAPPINGS.items()
}

