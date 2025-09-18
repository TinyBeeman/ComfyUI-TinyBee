import os
import random
import glob
import re
import json
import logging
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
        for line in enumerate(lines):
            line[1] = line[1].strip()
            # If the line is empty, skip it.
            if not line[1]:
                continue
            # If the line starts with "neg:", put it in the negative part for iPart
            if line[1].lower().startswith("neg:"):
                if iPart >= 0 and iPart < 5:
                    negs[iPart] = line[1]
                else:
                    logging.warning(f"Negative prompt found before any positive prompt: {line[1]}")
                    pass
            elif iPart < 5:
                parts[iPart] = line[1]
                iPart += 1

        if prefix_all.strip():
            parts = [prefix_all.strip() + " " + p for p in parts]
        if postfix_all.strip():
            parts = [p + " " + postfix_all.strip() for p in parts]
        if search_string:
            parts = [p.replace(search_string, replace_string) for p in parts]
            negs = [n.replace(search_string, replace_string) for n in negs]

        return (parts[0], negs[0], parts[1], negs[1], parts[2], negs[2], parts[3], negs[3], parts[4], negs[4])

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("prompt1", "neg1", "prompt2", "neg2", "prompt3", "neg3", "prompt4", "neg4", "prompt5", "neg5")
    # Mark each output explicitly as a non-list scalar to match all five outputs
    OUTPUT_IS_LIST = (False, False, False, False, False)
    FUNCTION = "splitPrompt"
    CATEGORY = "🐝TinyBee/Util"


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
    "Process Path Name": imp_processPathNameNode,
    "Random Entry": imp_randomListEntryNode,
    "Randomize List": imp_randomizeListNode,
    "Sort List": imp_sortListNode,

    "Incrementer": imp_incrementerNode,
    "Prompt Splitter": imp_promptSplitterNode,

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

    "imp_incrementerNode": "Incrementer",
    "imp_processPathNameNode": "Process Path Name",
    "imp_promptSplitterNode": "Prompt Splitter",
}
 

