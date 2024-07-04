#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   ver:    1.0
#   date:   18/04/2023
#   author: georgiana-bud


class PipelineMemory:
    def __init__(self):
        #   mem is an object, each of its property holds an array of opaque data object (they can be anything)
        self._mem = {}

    def properties(self):
        return list(self._mem.keys())
    
    def values(self):
        return self._mem.values()
    
    def items(self):
        return self._mem.items()
    
    def push_list_elements(self, prop, data):
        if not isinstance(data, list): 
            return
        
        if prop in self._mem:
            if data is None:
                return
            for el in data:
                self._mem[prop].append(el)
            
        else:
            self._mem[prop] = []
            
            if data is not None:   
                self._mem[prop] = []
                for el in data:
                    self._mem[prop].append(el)
            

    def push(self, prop, data):
        #   push an opaque data object into a mem property (add the property if it does not exist)
        if prop in self._mem:
            if data is None:
                return
            self._mem[prop].append(data)
            
        else:
            if data is None:
                self._mem[prop] = [] 
            else:   
                self._mem[prop] = [data]

    def get(self, prop):
        #   get a reference of an opaque data object from the mem, without removing it
        #   If the objects contained in the list returned by this method are modifiable, 
        #   the method can be used to modify the objects in place
        """
        data = []
        if property in self._mem:
            data = self._mem[property]
        """
        
        return self._mem.get(prop, [])

    def pop(self, prop):
        #   get an opaque obejct from the mem and remove it
        #  NOTE the following 5 lines do not eliminate the key from the dictionary;
        # this means the key will be present, and will point to an empty list; it is possible
        # to eliminate items while iterating
        #data = self.get(property)
        #if data != []:
        #    self._mem[property] = []
            #self._mem.pop(property, [])
        #return data
        # If the following is used instead of the above code, to eliminate items from
        # the dictionary while iterating through it, iterate on list(keys())
        return self._mem.pop(prop, [])

