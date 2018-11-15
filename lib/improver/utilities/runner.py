# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# (C) British Crown Copyright 2017-2018 Met Office.
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
""" Utilities to run plugins """

import dask.distributed
import iris


def apply_plugin(plugin, cubes):
    """
    A delayed runner for plugin classes/process methods.
    Parallelises the processing of a plugin over an iterator of cubes.


    Args:
        plugin (object):
            Plugin instance, or its process method to be executed.
        cubes (iterator):
            Cubes to be operated on by the plugin.

    Returns:
        results (iris.cube.CubeList):
            The results from the cubes acted on by the plugin.
    """

    # Allow the class to be called as well as the process method
    if not callable(plugin):
        if hasattr(plugin, 'process'):
            plugin = plugin.process

    # Initialise a distributed client (Not using processes to avoid pickling)
    client = dask.distributed.Client(processes=False, diagnostics_port=None)

    futures = client.map(plugin, cubes)
    results = client.gather(futures, asynchronous=False)
    client.close()
    return iris.cube.CubeList(results)