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
                "prefix_all": ("STRING", {"default": "", "multiline": True, "forceInput": False}),
                "prompts": ("STRING", {"default": "", "multiline": True, "forceInput": False}),
                "postfix_all": ("STRING", {"default": "", "multiline": True, "forceInput": False}),
                "search_string": ("STRING", {"default": "", "forceInput": False}),
                "replace_string": ("STRING", {"default": "", "forceInput": False}),
            }
        }
    
    @staticmethod
    def splitPrompt(prefix_all, prompts, postfix_all, search_string, replace_string):
        # Split the prompts by newlines, strip whitespace and skip empty lines after stripping
        parts = [p.strip() for p in prompts.split('\n') if p.strip()]
        if prefix_all.strip():
            parts = [prefix_all.strip() + " " + p for p in parts]
        if postfix_all.strip():
            parts = [p + " " + postfix_all.strip() for p in parts]
        if search_string:
            parts = [p.replace(search_string, replace_string) for p in parts]
        
        # Ensure we have exactly 5 parts
        while len(parts) < 5:
            parts.append("")
        return (parts[0], parts[1], parts[2], parts[3], parts[4])

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt1", "prompt2", "prompt3", "prompt4", "prompt5")
    OUTPUT_IS_LIST = (False,)
    FUNCTION = "splitPrompt"
    CATEGORY = "🐝TinyBee/Util"


# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
    "Filter List": imp_filterListNode,
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
 

