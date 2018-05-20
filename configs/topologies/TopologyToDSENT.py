# Author: David Smelt

import os
import subprocess

# Class for generating Tikz topology code,
# will be written to 'sim_output_directory/topo.tex'
# If imagemagick is installed, the topology is written to 'sim_output_directory/topology.png'

class TopologyToDSENT():
    def __init__(self, outdir, ijrate, nlinks, linkbits, nvcs, ncontrolbuffers, ndatabuffers):
        # Use different base names for texname and pngname
        routercfg = "router.cfg"
        linkcfg = "electrical-link.cfg"
        
        try:
            with open(os.path.join(outdir, routercfg), "w") as routerfile:
                routerfile.write("""
# Name of model to be built and evaluated
ModelName                               = Router

# Query string to choose what to evaluate (use '\\' to enable multiline config)
QueryString                             = \\
    Energy>>Router:WriteBuffer@0 \\
    Energy>>Router:ReadBuffer@0 \\
    Energy>>Router:TraverseCrossbar->Multicast1@0 \\
    Energy>>Router:ArbitrateSwitch->ArbitrateStage1@0 \\
    Energy>>Router:ArbitrateSwitch->ArbitrateStage2@0 \\
    Energy>>Router:DistributeClock@0 \\
    NddPower>>Router:Leakage@1 \\
    Area>>Router:Active@1 \\


# Injection rate (# flits per cycle per port), assuming that the router is not
# saturated
InjectionRate                           = {0}
# Evaluation string
EvaluateString                          = \\
    ejection_rate   = $(NumberInputPorts) * $(InjectionRate) / $(NumberOutputPorts); \\
    buf_rd_dynamic  = $(Energy>>Router:ReadBuffer) * $(Frequency); \\
    buf_wr_dynamic  = $(Energy>>Router:WriteBuffer) * $(Frequency); \\
    buf_static      = $(NddPower>>Router->InputPort:Leakage) * $(NumberInputPorts) + ($(NddPower>>Router->PipelineReg0:Leakage) + $(NddPower>>Router->PipelineReg1:Leakage)) * $(NumberInputPorts) * $(NumberBitsPerFlit); \\
    xbar_o_dynamic  = $(Energy>>Router:TraverseCrossbar->Multicast1) * $(Frequency); \\
    xbar_static     = $(NddPower>>Router->Crossbar:Leakage) + $(NddPower>>Router->PipelineReg2_0:Leakage) * $(NumberOutputPorts) * $(NumberBitsPerFlit); \\
    sa_o_dynamic    = ($(Energy>>Router:ArbitrateSwitch->ArbitrateStage1) + $(Energy>>Router:ArbitrateSwitch->ArbitrateStage2)) * $(Frequency); \\
    sa_static       = $(NddPower>>Router->SwitchAllocator:Leakage); \\
    clock_o_dynamic = $(Energy>>Router:DistributeClock) * $(Frequency); \\
    clock_static    = $(NddPower>>Router->ClockTree:Leakage); \\
    buffer_dynamic  = buf_wr_dynamic * $(InjectionRate) * $(NumberInputPorts) + buf_rd_dynamic * ejection_rate * $(NumberOutputPorts); \\
    buffer_leakage  = buf_static; \\
    xbar_dynamic    = xbar_o_dynamic * ejection_rate * $(NumberOutputPorts); \\
    xbar_leakage    = xbar_static; \\
    sa_dynamic      = sa_o_dynamic * ejection_rate * $(NumberOutputPorts); \\
    sa_leakage      = sa_static; \\
    clock_dynamic   = clock_o_dynamic; \\
    clock_leakage   = clock_static; \\
    total_dynamic   = buffer_dynamic + xbar_dynamic + sa_dynamic + clock_dynamic; \\
    total_leakage   = buffer_leakage + xbar_leakage + sa_leakage + clock_leakage; \\
    buf_area        = ($(Area>>Router->InputPort:Active) + ($(Area>>Router->PipelineReg0:Active) + $(Area>>Router->PipelineReg1:Active)) * $(NumberBitsPerFlit)) * $(NumberInputPorts); \\
    xbar_area       = $(Area>>Router->Crossbar:Active) + $(Area>>Router->Crossbar_Sel_DFF:Active) + $(Area>>Router->PipelineReg2_0:Active) * $(NumberBitsPerFlit) * $(NumberOutputPorts); \\
    sa_area         = $(Area>>Router->SwitchAllocator:Active); \\
    other_area      = $(Area>>Router->ClockTree:Active); \\
    print "Buffer:"; \\
    print "    Dynamic power: " buffer_dynamic; \\
    print "    Leakage power: " buffer_leakage; \\
    print "Crossbar:"; \\
    print "    Dynamic power: " xbar_dynamic; \\
    print "    Leakage power: " xbar_leakage; \\
    print "Switch allocator:"; \\
    print "    Dynamic power: " sa_dynamic; \\
    print "    Leakage power: " sa_leakage; \\
    print "Clock:"; \\
    print "    Dynamic power: " clock_dynamic; \\
    print "    Leakage power: " clock_leakage; \\
    print "Total:"; \\
    print "    Dynamic power: " total_dynamic; \\
    print "    Leakage power: " $(NddPower>>Router:Leakage); \\
    print "Area:"; \\
    print "    Buffer:           " buf_area; \\
    print "    Crossbar:         " xbar_area; \\
    print "    Switch allocator: " sa_area; \\
    print "    Other:            " other_area; \\

# Technology file (see other models in tech/models)
ElectricalTechModelFilename             = ext/dsent/tech/tech_models/Bulk45LVT.model

###############################################################################
# Timing optimization
###############################################################################

# True if want to perform timing optimization; otherwise, false.
IsPerformTimingOptimization             = true
# Nets that the timing optimizer starts from
TimingOptimization->StartNetNames       = [*]
# Operating frequency (Hz)
Frequency                               = 1.0e9

###############################################################################
# Model specifications
###############################################################################

# Number of input ports
NumberInputPorts                        = {1}
# Number of output ports
NumberOutputPorts                       = {1}
# Flit width (bit)
NumberBitsPerFlit                       = {2}

# In this example, we define 2 virtual networks (message classes), VN1 and VN2. 
#                           VN1 VN2
# Number of VCs              2   3
# Number of buffers / VC     4   5
#
# So in total, there are (2 * 4) + (3 * 5) = 23 flit buffers
#
# Number of virtual networks (number of message classes)
NumberVirtualNetworks                   = 3
# Number of virtual channels per virtual network
NumberVirtualChannelsPerVirtualNetwork  = [{3}, {3}, {3}]
# Number of buffers per virtual channel
NumberBuffersPerVirtualChannel          = [{4}, {4}, {5}]

# InputPort 
# ---------
# buffer model
InputPort->BufferModel                  = DFFRAM

# Crossbar
# --------
# crossbar model
CrossbarModel                           = MultiplexerCrossbar

# Switch allocator
# ----------------
# arbiter model
SwitchAllocator->ArbiterModel           = MatrixArbiter

# Clock tree
# ----------
# clock tree model
ClockTreeModel                          = BroadcastHTree
# number of levels
ClockTree->NumberLevels                 = 5
# wire layer
ClockTree->WireLayer                    = Global
# wire width multiplier
ClockTree->WireWidthMultiplier          = 1.0
""".format(ijrate, nlinks, linkbits, nvcs, ncontrolbuffers, ndatabuffers))

            with open(os.path.join(outdir, linkcfg), "w") as linkfile:
                linkfile.write("""
# Name of model to be built and evaluated
ModelName                               = RepeatedLink

# Query string to choose what to evaluate (use '\\' to enable multiline config)
QueryString                             = \\
    Energy>>RepeatedLink:Send@0 \\
    NddPower>>RepeatedLink:Leakage@0 \\
    Area>>RepeatedLink:Active@0 \\

# Injection rate
InjectionRate                           = {0}
# Evaluation string
EvaluateString                          = \\
    link_dynamic    = $(Energy>>RepeatedLink:Send) * $(Frequency); \\
    link_static     = $(NddPower>>RepeatedLink:Leakage); \\
    print "Link:"; \\
    print "    Dynamic power: " link_dynamic * $(InjectionRate); \\
    print "    Leakage power: " link_static; \\

# Technology file (see models in tech/models)
ElectricalTechModelFilename             = ext/dsent/tech/tech_models/Bulk45LVT.model

###############################################################################
# Timing optimization
###############################################################################

# True if want to perform timing optimization; otherwise, false.
# NOTE: for links it should never be turned on for timing optimization, the 
# link model is already doing timing optimization to insert buffers based on 
# the 'Delay' specified
IsPerformTimingOptimization             = false
# Nets that the timing optimizer starts from
TimingOptimization->StartNetNames       = []
# Operating frequency (Hz)
# 'Frequency' has no effect to the RepeatedLink model. Use 'Delay' to 
# constraint the links timing. 
Frequency                               = 1e9

###############################################################################
# Model specifications
###############################################################################

# Data width of the repeated link/bus
NumberBits                              = {1}
# Wire layer
WireLayer                               = Global
# Wire width multiplier
WireWidthMultiplier                     = 1.0
# Wire spacing multiplier
WireSpacingMultiplier                   = 1.0

# Wire length (m)
WireLength                              = 1e-3
# Delay of the wire (may not be 1.0 / Frequency)
Delay                                   = 1e-9
""".format(ijrate, linkbits))
        except IOError:
            return None
