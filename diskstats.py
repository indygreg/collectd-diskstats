#  Copyright 2010 Gregory Szorc
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
# This plugin reads data from /proc/diskstats
#
# It will only work on Linux 2.6
#
# To configure the plugin, you must specify the devices to monitor.
# The plugin takes a param 'Disk' whose string value is the exact
# device name. This param can be defined multiple times.
#
# e.g.
#
#<Plugin python>
#    ModulePath "/path/to/modules"
#    Import "diskstats"
#
#    <Module diskstats>
#        Disk sda
#        Disk sda1
#    </Module>
#</Plugin>
#
# The fields in /proc/diskstats are documented in Documentation/iostats.txt in
# the Linux kernel source tree.

import collectd

field_map = {
    1: 'reads_completed',
    2: 'reads_merged',
    3: 'sectors_read',
    4: 'reading_milliseconds',
    5: 'writes_completed',
    # this field not documented
    7: 'sectors_written',
    8: 'writing_milliseconds',
    9: 'io_inprogress',
    10: 'io_milliseconds',
    11: 'io_milliseconds_weighted'
}

disks = []

previous_values = {}

def diskstats_config(c):
    if c.values[0] != 'diskstats':
        return

    for child in c.children:
        if child.key == 'Disk':
            for v in child.values:
                if v not in disks:
                    disks.append(v)
                    if v not in previous_values:
                        previous_values[v] = {}

def diskstats_read(data=None):
    # if no disks to monitor, do nothing
    if not len(disks):
        return

    fh = open('/proc/diskstats', 'r')

    values = collectd.Values(type='gauge', plugin='diskstats')

    for line in fh:
        fields = line.split()

        if len(fields) != 14:
            collectd.warning('format of /proc/diskstats not recognized: %s' % line)
            continue

        device = fields[2]

        # are we monitoring this device?
        if device not in disks:
            continue

        for i in range(1, 12):
            # no mapping
            if i == 6:
                continue

            value = int(fields[i+2])

            # if this is the first value, simply record and move on to next field
            if i not in previous_values[device]:
                previous_values[device][i] = value
                continue

            # else we have a previous value
            previous_value = previous_values[device][i]

            delta = None

            # we have wrapped around
            if previous_value > value:
                delta = 4294967296 - previous_value + value
            else:
                delta = value - previous_value

            # field 9 is not a counter
            if i == 9:
                delta = value

            # record the new previous value
            previous_values[device][i] = value

            values.dispatch(plugin_instance=device, type_instance=field_map[i], values=[delta])

    fh.close()

collectd.register_read(diskstats_read)
collectd.register_config(diskstats_config)

