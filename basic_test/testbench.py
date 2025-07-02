from cocotb.triggers import Timer
from pyuvm import *
import random
import pyuvm
# All testbenches use tinyalu_utils, so store it in a central
# place and add its path to the sys path so we can import it
import sys
from pathlib import Path
sys.path.append(str(Path("..").resolve()))
from tinyalu_utils import TinyAluBfm, Ops, alu_prediction  # noqa: E402

sys.path.append(str(Path("../..").resolve()))
from uvm_packet import *
from uvm_network import *

class AluSeqItem(uvm_sequence_item):
    def __init__(self, name, aa, bb, op):
        super().__init__(name)
        self.A = aa
        self.B = bb
        self.op = Ops(op)

    def randomize_operands(self):
        self.A = random.randint(0, 255)
        self.B = random.randint(0, 255)

    def randomize(self):
        self.randomize_operands()
        self.op = random.choice(list(Ops))

    def __eq__(self, other):
        same = self.A == other.A and self.B == other.B and self.op == other.op
        return same

    def __str__(self):
        return f"{self.get_name()} : A: 0x{self.A:02x} \
        OP: {self.op.name} ({self.op.value}) B: 0x{self.B:02x}"


class RandomSeq(uvm_sequence):
    async def body(self):
        self.network = ConfigDB().get(None, "", "NETWORK")

        for _ in range(500):
            for op in list(Ops):
                cmd_tr = AluSeqItem("cmd_tr", None, None, op)
                cmd_tr.randomize_operands()
                await self.network.put_ack("sequencer","driver", cmd_tr) 
                
class Driver(uvm_driver):
    def build_phase(self):
        self.network = ConfigDB().get(None, "", "NETWORK")
        self.bfm     = ConfigDB().get(None, "", "BFM")
   
    async def launch_tb(self):
        await self.bfm.reset()
        self.bfm.start_bfm()
    
    async def proc_driver(self, pkt :uvm_packet) -> uvm_packet:
        req_obj = pkt.get_req_obj()
        await self.bfm.send_op(req_obj.A, req_obj.B, req_obj.op)
        pkt.set_state_done() #set to done for ack
        return pkt

    async def run_phase(self):
        await self.launch_tb()
        while True:
            await self.network.get("sequencer", "driver", self.proc_driver)

class CmdMonitor(uvm_monitor):
    def build_phase(self):
        self.network = ConfigDB().get(None, "", "NETWORK")
        self.bfm     = ConfigDB().get(None, "", "BFM")

    async def run_phase(self):
        while True:
            data = await self.bfm.get_cmd() 
            await self.network.put_noack("cmd_mon", "scoreboard", data)

class ResMonitor(uvm_monitor):    
    def build_phase(self):
        self.network = ConfigDB().get(None, "", "NETWORK")
        self.bfm     = ConfigDB().get(None, "", "BFM")

    async def run_phase(self):
        while True:
            data = await self.bfm.get_result() 
            await self.network.put_noack("res_mon", "scoreboard", data)

class Scoreboard(uvm_component):
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.cmdcnt    = 0
        self.resultcnt = 0
        self.passed    = True

    def build_phase(self):
        self.network = ConfigDB().get(None, "", "NETWORK")

    async def run_phase(self):
        while True:
            cmd_tmp = await self.network.get("cmd_mon","scoreboard") 
            res_tmp = await self.network.get("res_mon","scoreboard") 
                              
            (A, B, OP_val)   = cmd_tmp 
            OP               = Ops(OP_val)

            actual_result    = res_tmp
            predicted_result = alu_prediction(A, B, OP) 

            if predicted_result == actual_result:
                self.logger.info(f"PASSED: 0x{A:02x} {OP.name} 0x{B:02x} ="
                                 f" 0x{actual_result:04x}")
            else:
                self.logger.error(f"FAILED: 0x{A:02x} {OP.name} 0x{B:02x} "
                                  f"= 0x{actual_result:04x} "
                                  f"expected 0x{predicted_result:04x}")
                self.passed = False
                
            self.cmdcnt    += 1
            self.resultcnt += 1 

    def check_phase(self):
        
        if self.cmdcnt == 0:
            uvm_error("scoreboard", " no commands were sent")

        if self.resultcnt == 0:
            uvm_error("scoreboard", " no results were received")

        assert self.passed

class AluEnv(uvm_env):
    def build_phase(self):
        self.network    = uvm_network("network", self)
        ConfigDB().set(None, "*", "NETWORK", self.network)

        self.bfm        = TinyAluBfm()
        ConfigDB().set(None, "*", "BFM", self.bfm)

        self.driver     = Driver.create("driver", self)
        self.cmd_mon    = CmdMonitor("cmd_mon", self)
        self.res_mon    = ResMonitor("res_mon", self)
        self.scoreboard = Scoreboard("scoreboard", self)

    def connect_phase(self):
        self.network.add_path("sequencer", "driver"     )
        self.network.add_path("cmd_mon"  , "scoreboard" )
        self.network.add_path("res_mon"  , "scoreboard" ) 

@pyuvm.test()
class AluTest(uvm_test):
    """Test ALU with random and max values"""

    def build_phase(self):
        self.env = AluEnv("env", self)

    def end_of_elaboration_phase(self):
        self.test_all = RandomSeq.create("test_all")

    async def run_phase(self):
        self.raise_objection()
        await self.test_all.start()
        await Timer(100, units='us')
        self.drop_objection()