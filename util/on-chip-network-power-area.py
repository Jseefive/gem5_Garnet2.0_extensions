# Copyright (c) 2014 Mark D. Hill and David A. Wood
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from ConfigParser import ConfigParser
import string, sys, subprocess, os, re

# Compile DSENT to generate the Python module and then import it.
# This script assumes it is executed from the gem5 root.
print("Attempting compilation")
from subprocess import call

src_dir = 'ext/dsent'
build_dir = 'build/ext/dsent'

if not os.path.exists(build_dir):
    os.makedirs(build_dir)
os.chdir(build_dir)

error = call(['cmake', '../../../%s' % src_dir])
if error:
    print("Failed to run cmake")
    exit(-1)

error = call(['make'])
if error:
    print("Failed to run make")
    exit(-1)

print("Compiled dsent")
os.chdir("../../../")
sys.path.append("build/ext/dsent")
import dsent

# Parse gem5 config.ini file for the configuration parameters related to
# the on-chip network.
def parseConfig(config_file):
    config = ConfigParser()
    if not config.read(config_file):
        print("ERROR: config file '", config_file, "' not found")
        sys.exit(1)

    if not config.has_section("system.ruby.network"):
        print("ERROR: Ruby network not found in ", config_file)
        sys.exit(1)

    if config.get("system.ruby.network", "type") != "GarnetNetwork" :
        print("ERROR: Garnet network not used in ", config_file)
        sys.exit(1)

    number_of_virtual_networks = config.getint("system.ruby.network",
                                               "number_of_virtual_networks")
    vcs_per_vnet = config.getint("system.ruby.network", "vcs_per_vnet")

    buffers_per_data_vc = config.getint("system.ruby.network",
                                        "buffers_per_data_vc")
    buffers_per_control_vc = config.getint("system.ruby.network",
                                           "buffers_per_ctrl_vc")

    ni_flit_size_bits = 8 * config.getint("system.ruby.network",
                                          "ni_flit_size")

    routers = config.get("system.ruby.network", "routers").split()
    int_links = config.get("system.ruby.network", "int_links").split()
    ext_links = config.get("system.ruby.network", "ext_links").split()

    return (config, number_of_virtual_networks, vcs_per_vnet,
            buffers_per_data_vc, buffers_per_control_vc, ni_flit_size_bits,
            routers, int_links, ext_links)


def getClock(obj, config):
    if config.get(obj, "type") == "SrcClockDomain":
        return config.getint(obj, "clock")

    if config.get(obj, "type") == "DerivedClockDomain":
        source = config.get(obj, "clk_domain")
        divider = config.getint(obj, "clk_divider")
        return getClock(source, config)  / divider

    source = config.get(obj, "clk_domain")
    return getClock(source, config)


## Compute the power consumed by the given router
def computeRouterPowerAndArea(routers, stats_file, config, int_links, ext_links,
                              number_of_virtual_networks, vcs_per_vnet,
                              buffers_per_data_vc, buffers_per_control_vc,
                              ni_flit_size_bits):
    router_power = []
    for router in routers:
        frequency = getClock(router, config)

        # Count number of ports for this router
        nports = 0
        for int_link in int_links:
            if config.get(int_link, "src_node") == router or \
               config.get(int_link, "dst_node") == router:
               nports += 1

        for ext_link in ext_links:
            if config.get(ext_link, "int_node") == router:
               nports += 1

        print("\n%s:" % router)
        router_power.append(dsent.computeRouterPowerAndArea(
                                frequency, nports / 2, nports / 2,
                                number_of_virtual_networks, vcs_per_vnet,
                                buffers_per_control_vc, buffers_per_data_vc,
                                ni_flit_size_bits))
    
    # Calculate sum power of all routers
    print router_power
    sum_power = {}
    for power in router_power:
        print "power: ", power
        for elem in power:
            print "elem: ", elem
            if elem[1] > 0:
                if not elem[0] in sum_power:
                    sum_power[elem[0]] = elem[1]
                else:
                    sum_power[elem[0]] += elem[1]
    print sum_power
    print map(sum, sum_power)


## Compute the power consumed by the given int_links
def computeIntLinkPower(int_links, stats_file, config, sim_seconds):
    for link in int_links:
        frequency = getClock(link + ".credit_link", config)
        power = dsent.computeLinkPower(frequency)
        print("%s.credit_link Power: " % link, power)

        frequency = getClock(link + ".network_link", config)
        power = dsent.computeLinkPower(frequency)
        print("%s.network_link Power: " % link, power)


## Compute the power consumed by the given ext_links
def computeExtLinkPower(ext_links, stats_file, config, sim_seconds):
    for link in ext_links:
        frequency = getClock(link + ".credit_links0", config)
        power = dsent.computeLinkPower(frequency)
        print("%s.credit_links0 Power: " % link, power)

        frequency = getClock(link + ".credit_links1", config)
        power = dsent.computeLinkPower(frequency)
        print("%s.credit_links1 Power: " % link, power)

        frequency = getClock(link + ".network_links0", config)
        power = dsent.computeLinkPower(frequency)
        print("%s.network_links0 Power: " % link, power)

        frequency = getClock(link + ".network_links1", config)
        power = dsent.computeLinkPower(frequency)
        print("%s.network_links1 Power: " % link, power)


def parseStats(stats_file, config, router_config_file, link_config_file,
               routers, int_links, ext_links, number_of_virtual_networks,
               vcs_per_vnet, buffers_per_data_vc, buffers_per_control_vc,
               ni_flit_size_bits):

    # Open the stats.txt file and parse it to for the required numbers
    # and the number of routers.
    try:
        stats_handle = open(stats_file, 'r')
        stats_handle.close()
    except IOError:
        print("Failed to open ", stats_file, " for reading")
        exit(-1)

    # Now parse the stats
    pattern = "sim_seconds"
    lines = string.split(subprocess.check_output(
                ["grep", pattern, stats_file]), '\n', -1)
    assert len(lines) >= 1

    ## Assume that the first line is the one required
    [l1,l2,l3] = lines[0].partition(" ")
    l4 = l3.strip().partition(" ")
    simulation_length_in_seconds = float(l4[0])

    # Initialize DSENT with a configuration file
    dsent.initialize(router_config_file)

    # Compute the power consumed by the routers
    computeRouterPowerAndArea(routers, stats_file, config, int_links,
                              ext_links, number_of_virtual_networks,
                              vcs_per_vnet, buffers_per_data_vc,
                              buffers_per_control_vc, ni_flit_size_bits)

    # Finalize DSENT
    dsent.finalize()

    # Initialize DSENT with a configuration file
    dsent.initialize(link_config_file)

    # Compute the power consumed by the links
    #computeIntLinkPower(int_links, stats_file, config, simulation_length_in_seconds)
    #computeExtLinkPower(ext_links, stats_file, config, simulation_length_in_seconds)

    # Finalize DSENT
    dsent.finalize()

# This script parses the config.ini and the stats.txt from a run and
# generates the power and the area of the on-chip network using DSENT
def main():
    if len(sys.argv) < 2:
        print("Usage: ", sys.argv[0], " <simulation directory> " \
              "<router config file> <link config file>")
        exit(-1)

    print("WARNING: configuration files for DSENT and McPAT are separate. " \
          "Changes made to one are not reflected in the other.")

    cfg_str = os.path.join(sys.argv[1], "config.ini")
    stats_str = os.path.join(sys.argv[1], "stats.txt")

    (config, number_of_virtual_networks, vcs_per_vnet, buffers_per_data_vc,
     buffers_per_control_vc, ni_flit_size_bits, routers, int_links,
     ext_links) = parseConfig(cfg_str)

    router_cfg = os.path.join(sys.argv[1], "router.cfg")
    link_cfg = os.path.join(sys.argv[1], "electrical-link.cfg")

    if len(sys.argv) > 2:
        router_cfg = sys.argv[2]
    if len(sys.argv) > 3:
        link_cfg = sys.argv[3]

    parseStats(stats_str, config, router_cfg, link_cfg, routers, int_links, ext_links,
               number_of_virtual_networks, vcs_per_vnet, buffers_per_data_vc,
               buffers_per_control_vc, ni_flit_size_bits)

if __name__ == "__main__":
    main()
