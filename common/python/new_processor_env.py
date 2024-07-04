#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024

#   ver:    1.1
#   date:   01/07/2023
#   author: georgiana-bud

#   ver 1.1 
#   - clear separation between resource managers and other types of providers

from common.python.pipeline_memory import PipelineMemory
class ProcessorEnvs:
    """
    Environment variables for all the processors: 
    providers and pipeline stack memory space
    """ 
    

    def __init__(self): 
        self.__resource_managers = {
            'db_provider' : None, 
            'blk_provider' : None
        }

        self.__providers = {
            'crypto_providers' : None, 
            'logger_provider' : None,
            'integrity_provider' : None,
            'encoding_provider' : None
        }

        self.__stack = {
            'events' :  PipelineMemory(), 
            'data' :  PipelineMemory()  
        }

    @property
    def resource_managers(self):
        return self.__resource_managers 
    
    @property 
    def providers(self):
        return self.__providers 
    
    @property 
    def pipeline_stack(self):
        return self.__stack

    @property
    def events(self):
        return self.__stack.get('events', None)
    
    @events.setter
    def events(self, ec):
        self.__stack['events'] = ec
    
    def empty_events_stack(self):
        self.__stack['events'] = PipelineMemory()


    @property
    def data(self):
        return self.__stack.get('data', None)
    
    @data.setter
    def data(self, pm):
        self.__stack['data'] = pm
    
    def empty_data_stack(self): 
        self.__stack['data'] = PipelineMemory()

    @property
    def db_provider(self):
        return self.__resource_managers.get('db_provider', None)
    
    @db_provider.setter
    def db_provider(self, db_prov):
        if self.db_provider is None:
            self.__resource_managers['db_provider'] = db_prov

    @property
    def blk_provider(self):
        return self.__resource_managers.get('blk_provider', None)
    
    @blk_provider.setter
    def blk_provider(self, blk_prov):
        if self.blk_provider is None:
            self.__resource_managers['blk_provider'] = blk_prov

    @property
    def crypto_providers(self):
        return self.__providers.get('crypto_providers', None) 
    
    @crypto_providers.setter
    def crypto_providers(self, crypto_provs):
        if self.crypto_providers is None:
            self.__providers['crypto_providers'] = crypto_provs 


    @property
    def logger_provider(self):
        return self.__providers.get('logger_provider', None)
    
    @logger_provider.setter
    def logger_provider(self, logger):
        if self.logger_provider is None:
            self.__providers['logger_provider'] = logger
    
    @property
    def integrity_provider(self):
        return self.__providers.get('integrity_provider', None)

    @integrity_provider.setter
    def integrity_provider(self, val):
        if self.integrity_provider is None:
            self.__providers['integrity_provider'] = val

    @property
    def encoding_provider(self):
        return self.__providers.get('encoding_provider', None)

    @encoding_provider.setter
    def encoding_provider(self, val):
        if self.encoding_provider is None:
            self.__providers['encoding_provider'] = val
