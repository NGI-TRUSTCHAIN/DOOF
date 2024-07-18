#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

# version:  1.0
# date:     27/02/2024
# author:   georgiana


import argparse
import json
from typing import Tuple

from common.python.error import DopError, LogSeverity
from common.python.utils import DopUtils

"""
This is a module for loading the processors into the pipelines, by using the 
JSON configuration file for the worker, with MACROs support. 
"""


def get_args(argl = None):
    parser = argparse.ArgumentParser(description='Worker')
    parser.add_argument('-c',
                    '--config',
                    action="store",
                    required=False,
                    dest="config", help='path to config file')
    return parser.parse_args()



def _list_is_base_case(macro_list: list) -> bool:
    if len(macro_list) == 0:
        return True

    for element in macro_list:
        if not isinstance(element, dict):
            return False

    return True

def load_processor(proc_entry: dict) -> Tuple[DopError, object]:
    perr, processor =  DopUtils.load_provider(proc_entry) 
    if perr.isError():
        error = DopError(24215,"Error in loading processor.")
        error.perr = perr 
        return error, processor
    
    ps_confstring: str = proc_entry['configuration']
    per: DopError = processor.init(ps_confstring)

    if per.isError(): 
        error = DopError(24216,"Error in initializing processor.")
        error.perr = per
        return error, processor
    
    return DopError(), processor

def load_macro_base_case(loaded_macros: dict, macro_name: str, macro_list: list) -> list:
    """
    macro is list of dictionaries
    
    INPUT: 
        [{
            "path": "/home/ecosteer/dop/provider/python/TODO",
            "class": "AUTH-TODO",
            "configuration":"" 
        }]

    OUTPUT:
        list of classes 
        e.g. 
        ["AUTH-TODO"]
    """
    
    for element in macro_list:
        #  "Processor" is in class name 
        if "Processor" not in element['class']:
            # just a placeholder
            to_append = element['class']
        else:
            err, processor = load_processor(element)

            to_append = processor

        if macro_name in loaded_macros:
            loaded_macros[macro_name].append(to_append)
        else:
            loaded_macros[macro_name] = [to_append]

def load_macro_recursive(macros: dict, loaded_macros: dict, macro_name: str, macro_list: list):
        
    if _list_is_base_case(macro_list): #macros[macro_name]
        # Either macro_list contains only dictionaries, or has length 0
        load_macro_base_case(loaded_macros, macro_name, macro_list)     # the vertex points only to leaves (processors)
    
    else:
        # recursive step: macro_list contains references to other macros or has length > 0

        # make a sublist with first element of macro_list
        # if this is a base case --> load_macro_base_case
        # if it is not a base case --> it means it is another macro which needs to be made explicit
        #  check which macro it is --> 
        #  if it wasn't already loaded,
        #   call a function which loads the macro recursively in the loaded_macros ds 
        #  add the contents of the loaded macros to this macro as well (reference to same objects)
        #  
        #
        # call load_macro_recursive on remaining part of list
        
        temp = [macro_list[0]]  # [macros[macro_name][0]]
        if _list_is_base_case(temp):    
            load_macro_base_case(loaded_macros, macro_name, temp)

        else:
            internal_macro_name = temp[0][1:] # substring the $, as temp[0] = "$MACRO"
            
            
            if internal_macro_name not in loaded_macros:
                
                load_macro_recursive(macros, loaded_macros, internal_macro_name, macros[internal_macro_name])

            # Having loaded the providers indicated in the macro, I need to copy its contents in the list
            # of this macro as well
            # NOTE  Memory-efficiency: the memory occupation of the loaded_macros data structure 
            # depends on the contents to which each entry points to;
            # in case of the providers, there is only one instance of the provider so there is only a reference to it

            
            # NOTE This may copy something that was already copied, based on the macros
            # which were already loaded in a depth-first manner
            loaded_providers = loaded_macros[internal_macro_name]
            for provider in loaded_providers:
                if macro_name in loaded_macros:
                    loaded_macros[macro_name].append(provider)
                else: 
                    loaded_macros[macro_name] = [provider]
           
        load_macro_recursive(macros, loaded_macros, macro_name, macro_list[1:])



def load_macro_rec_iter(macros: dict, loaded_macros: dict, macro_name: str, macro_list: list):
        
    if _list_is_base_case(macro_list): #macros[macro_name]
        # Either macro_list contains only dictionaries, or has length 0
        load_macro_base_case(loaded_macros, macro_name, macro_list)     # the vertex points only to leaves (processors)
    
    else:
        # recursive step: macro_list contains references to other macros or has length > 0

        # iterate on all elements indicated by the macro, and check 

        # if this is a base case (macro indicates a list of processors) --> load_macro_base_case
        # if it is not a base case --> it means it is another macro which needs to be made explicit
        #  check which macro it is --> 
        #  if it wasn't already loaded,
        #   call a function which loads the macro recursively in the loaded_macros  
        #  add the contents of the loaded macros to this macro as well (reference to same objects)
        #  
        #
        # call load_macro_recursive on remaining part of list
        for element in macro_list:
            temp = [element]

            ## differentiate when there is a need to LOAD vs a need to COPY what was already loaded
            if _list_is_base_case(temp):
                """temp contains a processor that needs to be loaded under this macro"""
                load_macro_base_case(loaded_macros, macro_name, temp)
                # --> equivalent to 
                # load_macro_rec_iter(macros, loaded_macros, macro_name, temp)
            else:

                internal_macro_name = element[1:] # substring the $, as element = "$MACRO"
            
            
                if internal_macro_name not in loaded_macros:
                    
                    load_macro_rec_iter(macros, loaded_macros, internal_macro_name, macros[internal_macro_name])

                # Having loaded the providers indicated in the macro, I need to copy its contents in the list
                # of this macro as well
                # NOTE Memory-efficiency: the memory occupation of the loaded_macros data structure 
                # depends on the contents to which each entry points to;
                # in case of the providers, there is only one instance of the provider so there is only a reference to it
                 

                # NOTE This may copy something that was already copied, based on the macros
                # which were already loaded in a depth-first manner 
                
                loaded_providers = loaded_macros[internal_macro_name]
                for provider in loaded_providers:
                    if macro_name in loaded_macros:
                        loaded_macros[macro_name].append(provider)
                    else: 
                        loaded_macros[macro_name] = [provider]
           


def load_macros(macros_dictionary: dict, loaded_macros: dict):
    macro_names = macros_dictionary.keys()
    
    for macro_name, macro_list in macros_dictionary.items():
        if macro_name in loaded_macros: # vertex has been already visited
            # This macro was already loaded, e.g. in some point of the recursion
            continue

        load_macro_rec_iter(macros_dictionary, loaded_macros, macro_name, macro_list)
 

def is_macro(conf):
    if isinstance(conf, str) and conf.startswith("$"):
        return True
    return False


def detect_cycles_recursive(macros_dictionary, v, visited, recStack):
    visited[v] = True 
    recStack[v] = True 

    for adj in macros_dictionary[v]:
        if is_macro(adj):
            adj = adj[1:]
            if not visited[adj]: 
                if detect_cycles_recursive(macros_dictionary, adj, visited, recStack):
                    return True 
            elif recStack[adj]: 
                return True 
            
    recStack[v] = False
    return False
            

def macros_are_valid(macros_dictionary):
    visited =  {key: False for key in macros_dictionary}
    recStack = {key: False for key in macros_dictionary}

    for macro_name, macro_list in macros_dictionary.items():
        if not visited[macro_name]:
            if detect_cycles_recursive(macros_dictionary, macro_name, visited, recStack):
                return False 
        
    return True



def syntax_check(confFilePath, args):

    configuration_dict = {}
 
    try: 
        with open(confFilePath) as conf:
            configuration_dict: dict = json.loads(conf.read())
    except Exception as e :
        print(e)
        return DopError(24102,"Error in parsing the configuration file")
    
    
    macros: dict = configuration_dict['macros']
    cycles = macros_are_valid(macros)
    print(f"Macro contain cycles: {cycles}")

    
    macros: dict = configuration_dict['macros_not_supported']
    cycles = macros_are_valid(macros)
    print(f"Macros_not_supported contain cycles: {cycles}")

    
    macros: dict = configuration_dict['macros_processors']
    cycles = macros_are_valid(macros)
    print(f"Macros_processors contain cycles: {cycles}")


def load_processors(processors_configuration, loaded_macros):
    
    pipeline = {}
    for event, processors in processors_configuration.items(): 
         
        pipeline[event] = {"main": [], "finally": []}
        
        for k, pipelines in processors.items():
            for entry in pipelines: 
                if is_macro(entry):
                    # Assume macro was already loaded
                    macro = entry[1:]
                    macro_processors = loaded_macros.get(macro, None)
                    if macro_processors is not None:
                        pipeline[event][k].extend(macro_processors) #k = main/finally
                else:
                    perr, processor =  DopUtils.load_provider(entry) 
                    
                    if perr.isError(): 
                        error = DopError(24215,"Error in loading processor.")
                        error.perr = perr 
                        
                        return error
                    
                    ps_confstring: str = entry['configuration']
                    per: DopError = processor.init(ps_confstring)
                    if per.isError(): 
                        error = DopError(24216,"Error in initializing processor.")
                        error.perr = per
                        return error


                    pipeline[event][k].append(processor) #k = main/finally
        
    return pipeline

def main(confFilePath, args):

    print("hello")
    configuration_dict = {}
 
    try: 
        with open(confFilePath) as conf:
            configuration_dict: dict = json.loads(conf.read())
    except Exception as e :
        print(e)
        return DopError(24102,"Error in parsing the configuration file")
    

    #pipelines: dict = configuration_dict['pipelines']

    # First, identify all the MACROS and map each macro to a dictionary of
    # key - value pairs where the key is the name of the MACRO and the value is an array
    # of processors.
    # In case the MACRO contains an indication to another MACRO, the indicated MACRO should
    # be substituted by the base value it indicates (recursively)

    # external data structure to be populated recursively
    
    macros: dict = configuration_dict['macros']

    loaded_macros = {}
    load_macros(macros, loaded_macros)

    for key, value in loaded_macros.items():
        print(f"{key}: {value}")


    
    pipelines_dict = configuration_dict['pipelines']

    pipeline = load_processors(pipelines_dict,loaded_macros)
    for key, value in pipeline.items(): 
        print(f"{key}:\t\t {value}")




if __name__ == "__main__":
    args = get_args()
    if args.config:
        config_file = args.config
    else: 
        config_file = ""
    print(config_file)
    providers_to_stop = []
    error:DopError = main(config_file,[])