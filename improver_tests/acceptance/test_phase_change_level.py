# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# (C) British Crown Copyright 2017-2019 Met Office.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""
Tests for the phase-change-level CLI
"""

import pytest

from . import acceptance as acc

pytestmark = [pytest.mark.acc, acc.skip_if_kgo_missing]
CLI = acc.cli_name_with_dashes(__file__)
run_cli = acc.run_cli(CLI)


def test_snow_sleet(tmp_path):
    """Test snow/sleet level calculation"""
    kgo_dir = acc.kgo_root() / f"{CLI}/basic"
    kgo_path = kgo_dir / "snow_sleet_kgo.nc"
    output_path = tmp_path / "output.nc"
    input_paths = [kgo_dir / x for x in
                   ("wet_bulb_temperature.nc",
                    "wbti.nc",
                    "orog.nc",
                    "land_mask.nc")]
    args = [*input_paths,
            "--phase-change", "snow-sleet",
            "--output", output_path]
    run_cli(args)
    acc.compare(output_path, kgo_path)


def test_sleet_rain(tmp_path):
    """Test sleet/rain level calculation"""
    kgo_dir = acc.kgo_root() / f"{CLI}/basic"
    kgo_path = kgo_dir / "sleet_rain_kgo.nc"
    output_path = tmp_path / "output.nc"
    input_paths = [kgo_dir / x for x in
                   ("wet_bulb_temperature.nc",
                    "wbti.nc",
                    "orog.nc",
                    "land_mask.nc")]
    args = [*input_paths,
            "--phase-change", "sleet-rain",
            "--output", output_path]
    run_cli(args)
    acc.compare(output_path, kgo_path)


def test_sleet_rain_unfilled(tmp_path):
    """Test sleet/rain level calculation leaving below orography points
    unfilled."""
    kgo_dir = acc.kgo_root() / f"{CLI}/basic"
    kgo_path = kgo_dir / "sleet_rain_unfilled_kgo.nc"
    output_path = tmp_path / "output.nc"
    input_paths = [kgo_dir / x for x in
                   ("wet_bulb_temperature.nc",
                    "wbti.nc",
                    "orog.nc",
                    "land_mask.nc")]
    args = [*input_paths,
            "--phase-change", "sleet-rain",
            "--horizontal-interpolation", "False",
            "--output", output_path]
    run_cli(args)
    acc.compare(output_path, kgo_path)
