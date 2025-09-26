import os
import random
import glob
import re
import json
import logging
import datetime
from time import time

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

class imp_randomListEntryNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "seed": ("INT", {"default": -1, "min": -1, "max": 0xffffffffffffffff}),
                "string_list": ("STRING", {"forceInput": True}),
            }
        }
    
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
        return None
    
    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("Entry",)
    FUNCTION = "getRandomListEntry"
    CATEGORY = "🐝TinyBee/Lists"

class imp_indexedListEntryNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "index": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "string_list": ("STRING", {"forceInput": True}),
            }
        }
    
    @staticmethod
    def getIndexedListEntry(index, string_list):
        if (len(string_list) > 0):
            entry = string_list[index[0] % len(string_list)]
            return (entry,)
        return None
    
    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("Entry",)
    FUNCTION = "getIndexedListEntry"
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
            }
        }
    
    @staticmethod
    def getIndexedListEntry(index, string_list):
        if (len(string_list) > 0):
            entry = string_list[index[0] % len(string_list)]
            return (entry,)
        return None
    
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
            return None
        random.seed(seed[0])
        random.shuffle(string_list)
        return (string_list,)

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("randomized_list",)
    FUNCTION = "randomizeList"
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
            return None

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
            return None

        filtered = []
        for item in string_list:
            if string_filter[0] and string_filter[0] not in item:
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
            return None

        replaced = []
        for item in string_list:
            if search_string[0] and search_string[0] not in item:
                continue
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

class imp_splitListNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "combined_string": ("STRING", {"default": "", "forceInput": False, "multiline": True}),
                "delimiter": (["comma", "semicolon", "space", "newline", "custom"], {"default": "newline"}),
                "custom_delimiter": ("STRING", {"default": ";", "forceInput": False}),
            }
        }

    @staticmethod
    def splitList(combined_string, delimiter, custom_delimiter):
        # Normalize inputs from ComfyUI conventions (may come as single-item lists)
        if isinstance(delimiter, (list, tuple)) and delimiter:
            delimiter = delimiter[0]
        if isinstance(custom_delimiter, (list, tuple)) and custom_delimiter:
            custom_delimiter = custom_delimiter[0]

        s = ""
        if isinstance(combined_string, (list, tuple)):
            s = "\n".join(str(x) for x in combined_string)
        elif combined_string is None:
            s = ""
        else:
            s = str(combined_string)

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
    FUNCTION = "splitList"
    CATEGORY = "🐝TinyBee/Lists"

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
            return None

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
            }
        }

    @staticmethod
    def getFileList(path, glob_pattern, sort_method, sort_ascending, seed, allowed_extensions=None):
        # allowed_extensions: comma-separated string
        if allowed_extensions is None or allowed_extensions.strip() == "":
            allowed = []
        else:
            allowed = [ext.strip().lower() for ext in allowed_extensions.split(',') if ext.strip()]
        pattern = path.rstrip("/\\") + "/" + glob_pattern
        files = glob.glob(pattern, recursive=True)
        if (len(allowed) > 0):
            filtered = [f for f in files if any(f.lower().endswith(ext) for ext in allowed)]
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
        return (full_path, path_only, file_name_base, file_name_ext)

    RETURN_TYPES = ("STRING","STRING","STRING","STRING")
    RETURN_NAMES = ("full_path","path_only","file_name_base","file_name_ext")
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

class imp_timestampNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

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

# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
    "Filter List": imp_filterListNode,
    "Combine Lists": imp_combineListsNode,
    "Replace List": imp_replaceListNode,
    "Filter Existing Files": imp_filterFileExistsListNode,
    "Filter Words": imp_filterWordsNode,
    "Get File List": imp_getFileListNode,
    "Get List From File": imp_getListFromFileNode,
    "Indexed Entry": imp_indexedListEntryNode,
    "List Count": imp_listCountNode,
    "Random Entry": imp_randomListEntryNode,
    "Randomize List": imp_randomizeListNode,
    "Sort List": imp_sortListNode,
    "Split List": imp_splitListNode,

    "Process Path Name": imp_processPathNameNode,
    "Incrementer": imp_incrementerNode,
    "Prompt Splitter": imp_promptSplitterNode,
    "Timestamp": imp_timestampNode,
    "Force Aspect On Bounds": imp_forceAspectOnBoundsNode,
    "Select Bounding Box": imp_selectBoundingBoxNode,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "imp_filterListNode": "Filter List",
    "imp_combineListsNode": "Combine Lists",
    "imp_filterWordsNode": "Filter Words",
    "imp_filterFileExistsListNode": "Filter Existing Files",
    "imp_getFileListNode": "Get File List",
    "imp_getListFromFileNode": "Get List From File",
    "imp_indexedListEntryNode": "Indexed Entry",
    "imp_listCountNode": "List Count",
    "imp_randomizeListNode": "Randomize List",
    "imp_randomListEntryNode": "Random Entry",
    "imp_replaceListNode": "Replace List",
    "imp_sortListNode": "Sort List",
    "imp_splitListNode": "Split List",

    "imp_incrementerNode": "Incrementer",
    "imp_processPathNameNode": "Process Path Name",
    "imp_promptSplitterNode": "Prompt Splitter",
    "imp_timestampNode": "Timestamp",
    "imp_forceAspectOnBoundsNode": "Force Aspect On Bounds",
    "imp_selectBoundingBoxNode": "Select Bounding Box",
}
 



