.. _examples-label:

==========
Examples
==========

In the ``VegasFlow`` repository you can find `several examples <https://github.com/N3PDF/vegasflow/tree/master/examples>`_
of integrands which can hopefully help you to quickstart your project.

In this page we explain in more detail some of these examples.
You can find the full code in the repository alongside more complicated versions.


.. contents::
   :local:
   :depth: 1


Basic Integral
==============

The most general usage of ``Vegasflow`` is the integration of a tensorflow-based
integrand.

.. code-block:: python

    import tensorflow as tf

    @tf.function
    def my_integrand(xarr, **kwargs):
      return tf.reduce_sum(xarr, axis=1)
      
    from VegasFlow.vflow import vegas_wrapper

    n_dim = 10
    n_events = int(1e6)
    n_iter = 5
    result = vegas_wrapper(my_integrand, n_dim, n_iter, n_events)
            

You can find a `runnable example of such a basic example in the repository <https://github.com/N3PDF/vegasflow/blob/master/examples/simgauss_tf.py>`_.


Interfacing C code: CFFI
========================

A popular way of interfacing python and C code is to use the
`CFFI library  <https://cffi.readthedocs.io/en/latest/>`_.

Imagine you have a C-file with some integrand:

.. code-block:: C

    // integrand.c
    void integrand(double *xarr, int ndim, int nevents, double *out) {
        for (int i = 0; i < nevents; i++) {
            out[i] = 0.0;
            for (int j = 0; j < ndim; j++) {
                out[i] += 2.0*xarr[j+i*ndim];
            }
        }
    }
    
You can compile this code and integrate it (no pun intended) with ``vegasflow``
by using the CFFI library as you can see in `this <https://github.com/N3PDF/vegasflow/blob/master/examples/simgauss_cffi.py>`_ example.
            
.. code-block:: python

    from vegasflow.configflow import DTYPE
    import numpy as np
    from vegasflow.vflow import vegas_wrapper

    from cffi import FFI
    ffibuilder = FFI()
    
    ffibuilder.cdef("void integrand(double*, int, int, double*);")
    
    with open("integrand.c", "r") as f:
        ffibuilder.set_source("_integrand_cffi", f.read())
        
    ffibuilder.compile()
    
    # Now you can read up the compiled C code as a python library
    from _integrand_cffi import ffi, lib
    
    def integrand(xarr, n_dim, **kwargs):
        result = np.empty(n_events, dtype=DTYPE.as_numpy_dtype)
        x_flat = xarr.numpy().flatten()
        
        p_input = ffi.cast("double*", ffi.from_buffer(x_flat))
        p_output = ffi.cast("double*", ffi.from_buffer(result))
        
        lib.integrand(p_input, n_dim, xarr.shape[0], p_output)
        return result
        
    vegas_wrapper(integrand, 5, 10, int(1e5), compilable=False)
    
    
Note the usage of the ``compilable=False`` flag.
This signals ``VegasFlow`` that the integrand is not pure tensorflow and
that a graph of the full computation cannot be compiled.


Create your own TF-compilable operators
=======================================

Tensorflow tries to do its best to compile your integrand to something that can
quickly be evaluated on GPU.
It has no information, however, about specific situations that would allow
for non trivial optimizations.

In these cases one could want to write its own C++ or Cuda code while still
allowing for Tensorflow to create a full graph of the computation.

Creating new operations in TF are an advance feature and, when possible,
it is recommended to create your integrand as a composition of TF operators.
If you still want to go ahead we have prepared a `simple example <https://github.com/N3PDF/vegasflow/tree/master/examples/cuda>`_
in the repository that can be used as a template for C++ or Cuda custom
operators.

The example includes a `makefile <https://github.com/N3PDF/vegasflow/blob/master/examples/cuda/makefile>`_ that you might need to modify for your particular needs.

Note that in order to run the code in both GPUs and CPU you will need to provide
a GPU and CPU capable kernels.




