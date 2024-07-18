#   SPDX-License-Identifier: Apache-2.0

#   © Copyright Ecosteer 2024
#	auth:	graz
#	ver:	1.0
#	date:	06/06/2024


import sys

import signal
import os
import sys
import time
import json
import yaml
import importlib
from typing import Callable

from web3 import Web3
from web3.middleware import geth_poa_middleware
from abc import ABC, abstractmethod
from typing import Tuple

#   import from packages and modules within the ecosteer project 
from common.python.error import DopError
from common.python.event import DopEventHeader, DopEventPayload, DopEvent
from common.python.utils import DopUtils
from common.python.threads import DopStopEvent

from provider.python.presentation.output.provider_pres_output import outputPresentationProvider
from provider.python.intermediation.monitor.provider_monitor import blockchainMonitorProvider



#   USAGE:
#   python monitor.py configurationfile [idx=startblockidx]


class DOPEnvironment:
    def __init__(self):
        self.i_bcProvider = None        #   blockchain provider
        self.i_outProvider = None      #   presentation provider

    @property
    def bcProvider(self) -> blockchainMonitorProvider:
        return self.i_bcProvider

    @property
    def outProvider(self) -> outputPresentationProvider:
        return self.i_outProvider

    def setBlockchain(self, bcProvider: blockchainMonitorProvider):
        self.i_bcProvider = bcProvider

    def setOutput(self, outProvider: outputPresentationProvider):
        self.i_outProvider = outProvider




#   globals variables
#event_ExitEvent = Event()
#event_ExitEvent.clear()

globalStopEvent = DopStopEvent()


#def exiting() -> bool:
#    return event_ExitEvent.is_set()

        

def signalHandlerDefault(signalNumber, frame):
    print('Received:', signalNumber)

def progstop():
    print('Exiting ...')
    globalStopEvent.stop()

def signalHandlerExit(signalNumber, frame):
    #   set the exit event
    progstop()

def signalManagement():
    signal.signal(signal.SIGTERM, signalHandlerExit)
    signal.signal(signal.SIGINT, signalHandlerExit)
    signal.signal(signal.SIGQUIT, signalHandlerExit)

    #signal.signal(signal.SIGKILL, signalHandlerExit)

    #signal.signal(signal.SIGHUP, signalHandlerDefault)
    #signal.signal(signal.SIGINT, signalHandlerDefault)
    #signal.signal(signal.SIGQUIT, signalHandlerDefault)
    #signal.signal(signal.SIGILL, signalHandlerDefault)
    #signal.signal(signal.SIGTRAP, signalHandlerDefault)
    #signal.signal(signal.SIGABRT, signalHandlerDefault)
    #signal.signal(signal.SIGBUS, signalHandlerDefault)
    #signal.signal(signal.SIGFPE, signalHandlerDefault)
    
    #signal.signal(signal.SIGUSR1, signalHandlerDefault)
    #signal.signal(signal.SIGSEGV, signalHandlerDefault)
    #signal.signal(signal.SIGUSR2, signalHandlerDefault)
    #signal.signal(signal.SIGPIPE, signalHandlerDefault)
    #signal.signal(signal.SIGALRM, signalHandlerDefault)


def saveState(statusFile: str, lastBlockIndex: int) -> DopError:
    #   before exiting the process saves (stores to file) the
    #   last processed block index
    print('Saving status to ' + statusFile)
    try:
        with open(statusFile,'w+') as writer:
            writer.write(str(lastBlockIndex))
        return (DopError())
    except:
        return (DopError(1,"io open/write exception"))

def restoreStatus(statusfile: str) -> Tuple[DopError,int]:
    str_index: str = '0'

    if os.path.exists(statusfile) == False:
        return (DopError(1,'lastindex file does not exist'),0)

    try:
        with open(statusfile,'r') as reader:
            str_index = reader.readline(256)
        return(DopError(),int(str_index))        
    except:
        return(DopError(1,"io open exception"),0)

def match(topic: str, eventList: list) -> Tuple[bool,str]:
    upperTopic: str = topic.upper();
    #   print("TOPIC: [" + upperTopic + "]")
    for event in eventList:
        #   print("     EVENT:[" + event[2])
        if event[2] == upperTopic:
            #   returns the name of the venet (function name)
            return (True, event[0])
            break
    return (False,"")
    
def formatData(argdata: str) -> list:
    start = 0
    end = 64
    dlist = []
    datalen = len(argdata)
    while end<=datalen:
        dlist.append('0x' + argdata[start:end])
        start = start + 64
        end = end + 64
    return dlist

def process_block(environment: DOPEnvironment, configuration: dict, blockNumber: str):
    blockTuple = environment.bcProvider.getBlock(blockNumber)
    if blockTuple[0].code != 0:
        return blockTuple
    block: dict = blockTuple[1]
    #   check if the block contains transactions
    transactions: list = block['transactions']
    #   transaction is a list containing all the transactions' ids present
    #   within the block
    if len(transactions)>0:
        print('block number ' + str(block['number']))
        for tr in transactions:
            #   the block holds at least one transaction so every transaction
            #   in the block has to be scanned, to check presence of 
            #   a)  events emitted by smart contracts or
            #   b)  creation of new smart contract
            print(tr.hex())
            #   check transaction receipt
            receiptTuple = environment.bcProvider.getTransactionReceipt(tr)
            if receiptTuple[0].code == 0:
                transactionReceipt: dict = receiptTuple[1]

                #====================================================================================
                #   the transaction receipt has been found, check if it has smart contract address
                #====================================================================================
                contractAddress = transactionReceipt['contractAddress']
                if contractAddress != None:
                    #   topics have been found, data should be available
                    eh: DopEventHeader = DopEventHeader("-","-","event_set")
                    ep: DopEventPayload = DopEventPayload({'transaction_id':tr.hex(),'product_address':contractAddress})
                    ev: DopEvent = DopEvent(eh,ep)

                    #   send the event using the presentation provider (output provider)
                    #   new version: the write methods accepts a string, not a DopEvent 
                    err: DopError = environment.outProvider.write(str(ev))
                    #   here you can check if the error is recoverable
                    if err.isError():
                        print(err.msg)

                #====================================================================================
                #   the transaction receipt has been found, check if it has logs
                #====================================================================================
                transactionLogs: list = transactionReceipt['logs']

                event_list: list = []
                if len(transactionLogs)>0:
                    
                    for rlog in transactionLogs:
                        log = dict(rlog)
                        topics: list = log['topics']
                        #   check every single topic
                        
                        
                        for topic in topics:
                            #   every topic in the list is checked to see if it matches
                            #   with one of the available event signatures
                            matchTuple = match(topic.hex(), configuration['INTERNAL_events'])
                            #   matchTuple[0]:  bool, True if matches
                            #   matchTuple[1]:  if matches, contains the human readable event name
                            if matchTuple[0] == True:
                                print('MATCH ' + matchTuple[1] + ' ' + topic.hex())
                                data: str = log['data'].split('x')[1]
                                dataList = formatData(data)

                                event_element = {'event_id':matchTuple[1], 'data':dataList}
                                event_list.append(event_element)

                                #   print('DATA  ' + log['data'])
                                idx: int = 0
                                for d in dataList:
                                    print('ARG ' + str(idx) + ' ' + dataList[idx])
                                    idx = idx + 1


                if len(event_list) > 0:
                    #   topics have been found, data should be available
                    eh: DopEventHeader = DopEventHeader("-","-","event_set")
                    ep: DopEventPayload = DopEventPayload({'transaction_id':tr.hex(),'event_set':event_list})
                    ev: DopEvent = DopEvent(eh,ep)

                    #   send the event using the presentation provider (output provider)
                    #   new version: the write methods accepts a string, not a DopEvent 
                    err: DopError = environment.outProvider.write(str(ev))
                    #   here you can check if the error is recoverable
                    if err.isError():
                        print(err.msg)

                    #   reset the event list                        
                    event_list = []
                            
    return blockTuple


def getLastBlockIndex(environment: DOPEnvironment) -> Tuple[DopError, int]:
    blockTuple = environment.bcProvider.getBlock('latest')
    if blockTuple[0].code != 0:
        return (blockTuple[0],0)
    return (DopError(),blockTuple[1]['number'])

def eventSignature(bcProvider: blockchainMonitorProvider, eventDeclaration: str) -> Tuple[DopError,list]:
    #   eventDeclaration is the event synopsis, as, for example, the following string:
    #   HasSubscribed		(address _subscriber, address _product)
    #   Please note that the event declaration can be copied as it is 
    #   from the solidity source file
    #   NOTE:   please leave a space between the log event name and the first bracket

    #   1)  get the arglist
    arglist: list = ((eventDeclaration.split('(')[1]).split(')')[0]).split(',')
    str_buffer: list = ['(']
    
    #   2)  extract the type from every args
    for arg in arglist:
        arg_temp = arg.strip()
        for c in arg_temp:
            if (c==' ' or c=='\t'):
                break
            else:
                str_buffer.append(c)
        str_buffer.append(',')

    str_buffer[len(str_buffer)-1]=')'

    name_buffer: str = eventDeclaration.lstrip()
    event_name: str = ''
    for c in name_buffer:
        if (c==' ' or c=='\t'):
            break
        else:
            event_name = event_name + c
    
    event_args: str = "".join(str_buffer)
    event_signature = event_name + event_args
    hexSHA3: str = ''
    tupleHash = bcProvider.getHash('sha3', event_signature)
    if tupleHash[0].code != 0:
        return (tupleHash[0],[])
    else:
        hexSHA3 = tupleHash[1].upper()

    return (DopError(),[event_name, event_signature, hexSHA3])

def load_provider(config: dict) -> Tuple[DopError, Callable]:
    """
    Return a new provider given the configuration options as
     {
         'module': ...,
         'provider': ...,
         'configuration': ...
     }
    :param _config: dict object containing module, provider
                    and configuration options
    :return: Provider
    """
    
    if 'module' in config == False:
        return (DopError(1,"configuration missing module key"),None)
    conf_module = config['module']

    has_class = ('class' in config)
    has_provider = ('provider' in config)
    if (has_class or has_provider) == False:
        return (DopError(2,"configuration missing class key"),None)

    conf_provider: str = config['provider'] if has_provider else config['class']
    
    try:
        module = importlib.import_module(conf_module)
        provider = getattr(module, conf_provider)
        return (DopError(),provider())
    except:
        return (DopError(3,"exception while loading provider"),None)
    


def mainLoop(environment: DOPEnvironment, configuration: dict) -> DopError:
    #   within the main loop
    #   1)  the first block that has not been processed yet is extracted
    #   2)  the extracted block is matched against the event pattern
    #   3)  if a match is found, then the match is propagated to the output presentation provider

    #   start block index (INTERNAL_blockIndex) has been provided
    #   by the main routine
    i_startBlock: int = int(configuration['process']['INTERNAL_blockIndex'])
    i_scanDelay: int = int(configuration['process']['scandelay'])

    #debug purposes
        #   for debug purposes only
    eventSignatures: list = configuration['INTERNAL_events']
    for i in eventSignatures:
        print(i)


    #   get last block
    lastBlockTuple = getLastBlockIndex(environment)
    if lastBlockTuple[0].code != 0:
        return lastBlockTuple[0]

    i_endBlock: int = lastBlockTuple[1]
    if i_endBlock<i_startBlock:
        i_startBlock = i_endBlock

    while True:
        if globalStopEvent.is_exiting():
            break
        
        #   blockTuple
        #   [0] DopError, [1] dict containing a block
        blockTuple = process_block(environment, configuration, str(i_startBlock))
        if blockTuple[0].code != 0:
            print(blockTuple[0].msg)
            if blockTuple[0].isRecoverable() == False:
                print('unrecoverable error')
                #   the error is not recoverable
                #   the mainloop has to quite (soft exit)
                progstop()
            else:
                print('recoverable error')

        else:
            i_startBlock += 1
            print(blockTuple[1]['number'])

            #   if our block index (i_startBlock) is greater than the
            #   previosuly exctracted last block index, the get the current
            #   last block index (wait if there is no new block after the
            #   one that we have exctracted already)

            while i_startBlock > i_endBlock:
                lastBlockTuple = getLastBlockIndex(environment)

                if lastBlockTuple[0].code != 0:
                    
                    break

                i_endBlock = lastBlockTuple[1]
                if i_startBlock <= i_endBlock:
                    break
                else:
                    time.sleep(i_scanDelay)

    statusFile: str = configuration['process']['indexfile']
    err: DopError = saveState(statusFile, i_startBlock)
    return err


def parseArguments(arguments: list) -> dict:
    options: dict = {}
    if len(arguments)<1:
        return options
    for arg in arguments:
        arglist: list = arg.split('=')
        print(arglist)
        if len(arglist)>1:
            options.update({arglist[0]:arglist[1]})
    return options        




def main(confFilePath: str, arguments: list) -> DopError:
    
    options: dict = parseArguments(arguments)

    configurationTuple = DopUtils.parse_yaml_configuration(confFilePath)
    if configurationTuple[0].code != 0:
        return configurationTuple[0]

    #   configuration file has been successfuly parsed
    configuration: dict = configurationTuple[1]


    #=================================================================
    #   allocate and initialize the blockchainMonitorProvider
    #=================================================================
    #tupleLoadProvider = load_provider(configuration['blockchainMonitorProvider'])
    eth_conf: dict = configuration['blockchainMonitorProvider']
    tupleLoadProvider = DopUtils.load_provider(eth_conf)
    if tupleLoadProvider[0].isError():
        return tupleLoadProvider[0]
    eth_provider = tupleLoadProvider[1]
    #   the provider has been loaded, now it has to be initialized/configured

    blockchainConnstring: str = configuration['blockchainMonitorProvider']['configuration']
    err: DopError = eth_provider.init(blockchainConnstring)
    if err.code != 0:
        return err

    #=================================================================
    #   allocate and initialize the outputPresentationPRovider
    #=================================================================

    #tupleLoadProvider = load_provider(configuration['outputProvider'])
    output_conf: dict  = configuration['outputProvider']
    tupleLoadProvider = DopUtils.load_provider(output_conf)
    if tupleLoadProvider[0].isError():
        return tupleLoadProvider[0]
    out_provider = tupleLoadProvider[1]
    #   the provider has been loaded, now it has to be initialized/configured
    outputConnstring: str = configuration['outputProvider']['configuration']
    #out_provider = outputStdStream()
    err = out_provider.init(outputConnstring)
    if err.code != 0:
        return err


    #=================================================================
    #   open the providers
    #=================================================================
    print("opening eth provider")
    err = eth_provider.open()
    if err.isError():
        return err

    print("opening out provider")
    err = out_provider.open()
    if err.isError():
        return err

    #=================================================================
    #   attach a stop event to the providers
    #=================================================================
    eth_provider.attach_stop_event(globalStopEvent)
    out_provider.attach_stop_event(globalStopEvent)

    #=================================================================
    #   push the blockcain providers to the DOPEnvironment
    #=================================================================
    environment: DOPEnvironment = DOPEnvironment()
    environment.setBlockchain(eth_provider)
    environment.setOutput(out_provider)

    
    
    #=================================================================
    #   process events synopsis and calculate signatures
    #=================================================================
    eventSignatures: list = []
    eventList: list = configuration['events']
    
    for eventItem in eventList:
        tupleSignature = eventSignature(eth_provider,eventItem)
        if tupleSignature[0].code != 0:
            return tupleSignature[0]
        eventSignatures.append(tupleSignature[1])
    #   all calculated event signatures are now available in conf['INTERNAL_events']
    configuration['INTERNAL_events']=eventSignatures


    #=================================================================
    #   calculate block start index
    #=================================================================
    #   if a start index is passed as an arg, then the arg is used,
    #   otherwise the lastindex file is used (if it exists),
    #   otherwise the last block is used
    i_block_index: int = 0
    
    if 'idx' in options:
        i_block_index = int(options['idx'])
    else:
        #   the block index has not been explicitely passed
        #   in the prog arguments list, so try using the lastindex file        
        statusFile = configuration['process']['indexfile']
        
        if os.path.exists(statusFile) == False:
            #   the status file does not exists
            #   get (calculate) the last block
            lastBlockTuple = getLastBlockIndex(environment)
            i_block_index = lastBlockTuple[1]
            if lastBlockTuple[0].isError():
                # whatever
                return lastBlockTuple[0]
        else:
            #   restore last block from lastindex file
            tupleRestore = restoreStatus(statusFile)
            i_block_index = tupleRestore[1]
            if tupleRestore[0].isError():
                #   error accessing the status file
                return tupleRestore[0]        

    # calculated or restored block start index now available 
    # in conf['INTERNAL_blockIndex']   
    configuration['process']['INTERNAL_blockIndex'] = i_block_index


    #   check other parameters
    #   scandelay
    if 'scandelay' in configuration['process']:
        pass
    else:
        #   set default value
        configuration['process']['scandelay'] = 2
        
    #=================================================================
    #   start the mainLoop
    #=================================================================
    err = mainLoop(environment,configuration)


    #=================================================================
    #   close all the providers
    #=================================================================
    environment.bcProvider.close()
    environment.outProvider.close()


    return err

if __name__ == "__main__":
    #   python monitor.py %fileconf idx=%startidx
    #   %fileconf   MANDATORY       path of the configuration file
    #   %startidx   OPTIONAL        number (index) of the first block to 
    #                               be exctracted and processed
    #   examples:
    #       python monitor.py monitor.conf idx=2657000
    #       python monitor.py monitor.conf

    signalManagement()
    error: DopError = main(sys.argv[1], sys.argv[2:])
    if error.code != 0:
        print(error.msg)

