#include "Python.h"
#include <stdlib.h>
#include <limits.h>

#define VERSION "1.0.0"

static int enabled = 0;
static int installed = 0;

#if PY_VERSION_HEX >= 0x03050000
#  define FAIL_CALLOC
#  define PyMemAllocator PyMemAllocatorEx
#endif

struct {
    PyMemAllocator obj;
} hook;

static __thread unsigned long long allocs = 0;
static __thread unsigned long long callocs = 0;
static __thread unsigned long long reallocs = 0;
static __thread unsigned long long frees = 0;

static void* hook_malloc(void *ctx, size_t size)
{
    if (allocs == ULLONG_MAX) {
        allocs = 0;
    }

    allocs++;
    PyMemAllocator *alloc = (PyMemAllocator *)ctx;
    return alloc->malloc(alloc->ctx, size);
}

#ifdef FAIL_CALLOC
static void* hook_calloc(void *ctx, size_t nelem, size_t elsize)
{
    if (callocs == ULLONG_MAX) {
        callocs = 0;
    }

    callocs++;
    PyMemAllocator *alloc = (PyMemAllocator *)ctx;
    return alloc->calloc(alloc->ctx, nelem, elsize);
}
#endif

static void* hook_realloc(void *ctx, void *ptr, size_t new_size)
{
    if (reallocs == ULLONG_MAX) {
        reallocs = 0;
    }

    reallocs++;
    PyMemAllocator *alloc = (PyMemAllocator *)ctx;
    return alloc->realloc(alloc->ctx, ptr, new_size);
}

static void hook_free(void *ctx, void *ptr)
{
    if (frees == ULLONG_MAX) {
        frees = 0;
    }

    frees++;
    PyMemAllocator *alloc = (PyMemAllocator *)ctx;
    alloc->free(alloc->ctx, ptr);
}

static void setup_hooks(void)
{
    PyMemAllocator alloc;

    alloc.malloc = hook_malloc;
#ifdef FAIL_CALLOC
    alloc.calloc = hook_calloc;
#endif
    alloc.realloc = hook_realloc;
    alloc.free = hook_free;
    PyMem_GetAllocator(PYMEM_DOMAIN_OBJ, &hook.obj);

    alloc.ctx = &hook.obj;
    PyMem_SetAllocator(PYMEM_DOMAIN_OBJ, &alloc);
}

static void remove_hooks(void)
{
    PyMem_SetAllocator(PYMEM_DOMAIN_OBJ, &hook.obj);
}

static PyObject*
objtrace_enable(PyObject *module)
{
    enabled = 1;
    if (!installed) {
        installed = 1;
        setup_hooks();
    }
    Py_RETURN_NONE;
}

static PyObject*
objtrace_disable(PyObject *module)
{
    if (installed) {
        installed = 0;
        remove_hooks();
    }
    enabled = 0;
    Py_RETURN_NONE;
}

static PyObject*
objtrace_get_counts(PyObject *module)
{
    return Py_BuildValue("KKKK", allocs, callocs, reallocs, frees);
}

static PyObject*
objtrace_reset_counts(PyObject *module)
{
    allocs = 0;
    callocs = 0;
    reallocs = 0;
    frees = 0;

    Py_RETURN_NONE;
}

PyDoc_STRVAR(module_doc,
"scout_apm.core.objtrace module.");

static PyMethodDef module_methods[] = {
    {"enable",
     (PyCFunction)objtrace_enable, METH_NOARGS,
     PyDoc_STR("enable()")},
    {"disable",
     (PyCFunction)objtrace_disable, METH_NOARGS,
     PyDoc_STR("disable()")},
    {"get_counts",
     (PyCFunction)objtrace_get_counts, METH_NOARGS,
     PyDoc_STR("get_counts()")},
    {"reset_counts",
     (PyCFunction)objtrace_reset_counts, METH_NOARGS,
     PyDoc_STR("reset_counts()")},
    {NULL, NULL}  /* sentinel */
};

static struct PyModuleDef module_def = {
    PyModuleDef_HEAD_INIT,
    "scout_apm.core.objtrace",
    module_doc,
    0, /* non-negative size to be able to unload the module */
    module_methods,
    NULL,
    NULL,
    NULL,
    NULL
};

PyMODINIT_FUNC
PyInit_objtrace(void)
{
    PyObject *m, *version;

    m = PyModule_Create(&module_def);
    if (m == NULL)
        return NULL;

    version = PyUnicode_FromString(VERSION);
    if (version == NULL)
        return NULL;

    PyModule_AddObject(m, "__version__", version);
    return m;
}

