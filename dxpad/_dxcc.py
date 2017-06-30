#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Load file online from http://www.country-files.com/cty/cty.dat
For detailed information about the format see http://www.country-files.com/cty-dat-format/

First line information, fields are separated by ":"
Column  Length  Description
1       26      Country Name
27      5       CQ Zone
32      5       ITU Zone
37      5       2-letter continent abbreviation
42      9       Latitude in degrees, + for North
51      10      Longitude in degrees, + for West
61      9       Local time offset from GMT
70      6       Primary DXCC Prefix (A "*" preceding this prefix indicates that the country is on the DARC WAEDC list, and counts in CQ-sponsored contests, but not ARRL-sponsored contests).

Following lines contain alias DXCC prefixes (including the primary one), separated by commas (,).
Multiple lines are OK; a line to be continued should end with comma (,) though it's not required.
A semi-colon (;) terminates the last alias prefix in the list.

If an alias prefix is preceded by "=", this indicates that the prefix is to be treated as a full callsign, i.e. must be an exact match.

The following special characters can be applied after an alias prefix:
(#)     Override CQ Zone
[#]     Override ITU Zone
<#/#>   Override latitude/longitude
{aa}    Override Continent
~#~     Override local time offset from GMT

For detailed information about handling of prefixes and suffixes see http://www.cqwpx.com/rules.htm and http://svn.fkurz.net/dxcc/trunk/dxcc?view=markup
"""

import sys, os, re, requests

from . import _location, _config

class DXCCInfo:
    def __init__(self, name, cq_zone, itu_zone, continent, latlon, time_offset, primary_prefix):
        self.name = name
        self.cq_zone = cq_zone
        self.itu_zone = itu_zone
        self.continent = continent
        self.latlon = latlon
        self.time_offset = time_offset
        self.primary_prefix = primary_prefix
        self.needs_exact_match = False

    def copy(self):
        return DXCCInfo(
            self.name, 
            self.cq_zone,
            self.itu_zone,
            self.continent,
            self.latlon,
            self.time_offset,
            self.primary_prefix
        )

    def __str__(self):
        return "dxcc({}, cq={}, itu={}, cont={}, lat/lon={!s}, offset={:3.1f}, primary={}, exact={})".format(self.name, self.cq_zone, self.itu_zone, self.continent, self.latlon, self.time_offset, self.primary_prefix, self.needs_exact_match)

class DXCC:
    def __init__(self):
        self.infos_by_prefix = {}

    def _parse_dxcc_info(self, line):
        fields = line.split(":")
        name = fields[0].strip()
        cq_zone = int(fields[1].strip())
        itu_zone = int(fields[2].strip())
        continent = fields[3].strip()
        lat = float(fields[4].strip())
        lon = float(fields[5].strip()) * -1.0
        latlon = _location.LatLon(lat, lon)
        time_offset = float(fields[6].strip())
        primary_prefix = fields[7].strip()
        return DXCCInfo(name, cq_zone, itu_zone, continent, latlon, time_offset, primary_prefix)

    def _parse_prefixes(self, line, base_dxcc_info):
        prefixes = re.split(",|;", line)
        result = []
        for prefix in prefixes:
            if prefix.strip() == "":
                continue
            result.append(self._parse_prefix(prefix.strip(), base_dxcc_info))
        return result

    def _parse_prefix(self, text, base_dxcc_info):
        dxcc_info = base_dxcc_info.copy()
        prefix = text
        if prefix.startswith("="):
            dxcc_info.needs_exact_match = True
            prefix = prefix[1:]

        cq_override = re.search(r'\((\d+)\)', prefix)
        if cq_override:
            dxcc_info.cq_zone = int(cq_override.group(1))
            prefix = prefix.replace(cq_override.group(0), '')

        itu_override = re.search(r'\[(\d+)\]', prefix)
        if itu_override:
            dxcc_info.itu_zone = int(itu_override.group(1))
            prefix = prefix.replace(itu_override.group(0), '')

        latlon_override = re.search(r'\<(-?\d+.\d+)/(-?\d+.\d+)\>', prefix)
        if latlon_override:
            dxcc_info.lat = float(latlon_override.group(1))
            dxcc_info.lat = float(latlon_override.group(2))
            prefix = prefix.replace(latlon_override.group(0), '')

        continent_override = re.search(r'\{(\w+)\}', prefix)
        if continent_override:
            dxcc_info.continent = continent_override.group(1)
            prefix = prefix.replace(continent_override.group(0), '')

        time_offset_override = re.search(r'\~(-?\d+.\d+)\~', prefix)
        if time_offset_override:
            dxcc_info.time_offset = float(time_offset_override.group(1))
            prefix = prefix.replace(time_offset_override.group(0), '')

        return (prefix, dxcc_info)

    def load_from_file(self, filename):
        infos_by_prefix = {}

        next_country = True
        dxcc_info = None
        with open(filename) as f:
            for line in f:
                if next_country:
                    next_country = False
                    dxcc_info = self._parse_dxcc_info(line)
                else:
                    prefix_infos = self._parse_prefixes(line, dxcc_info)
                    for info in prefix_infos:
                        infos_by_prefix[info[0]] = info[1]
                    if line.strip().endswith(";"):
                        next_country = True

        self.infos_by_prefix = infos_by_prefix

    @staticmethod
    def download_cty_file():
        cty = requests.get("http://www.country-files.com/cty/cty.dat")
        filename = _config.filename("cty.dat")
        with open(filename, "w") as f:
            f.write(cty.text)

    def load(self):
        filename = _config.filename("cty.dat")
        if not os.path.isfile(filename):
            DXCC.download_cty_file()
        self.load_from_file(filename)

    def find_dxcc_info(self, call):
        prefix = str(call).upper()
        is_exact_match = True
        while len(prefix) > 0:
            if prefix in self.infos_by_prefix:
                dxcc_info = self.infos_by_prefix[prefix]
                if dxcc_info.needs_exact_match and not is_exact_match:
                    dxcc_info = None
                else:
                    return dxcc_info

            prefix = prefix[:-1]
            is_exact_match = False

        return None

def main():
    dxcc = DXCC()
    dxcc.load()
    for arg in sys.argv[1:]:
        dxcc_info = dxcc.find_dxcc_info(arg)
        print(("{:<10} {}".format(arg, str(dxcc_info))))

if __name__ == "__main__": main()