#include "Python.h"
#include <stdlib.h>
#include <limits.h>

#define VERSION "1.0.0"

#if PY_VERSION_HEX >= 0x03050000
// Config state
typedef struct {
    int enabled;
    int installed;
} _objtrace_config_state;

static inline _objtrace_config_state*
get_objtrace_config_state(PyObject *module)
{
    void *state = PyModule_GetState(module);
    assert(state != NULL);
    return (_objtrace_config_state *)state;
}
#else
static int enabled = 0;
static int installed = 0;
#endif

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
#if PY_VERSION_HEX >= 0x03050000
    _objtrace_config_state *state = get_objtrace_config_state(module);
    state->enabled = 1;
    if (!state->installed) {
        state->installed = 1;
        setup_hooks();
    }
#else
    enabled = 1;
    if (!installed) {
        installed = 1;
        setup_hooks();
    }
#endif
    Py_RETURN_NONE;
}

static PyObject*
objtrace_disable(PyObject *module)
{
#if PY_VERSION_HEX >= 0x03050000
    _objtrace_config_state *state = get_objtrace_config_state(module);
    if (state->installed) {
        state->installed = 0;
        remove_hooks();
    }
    state->enabled = 0;
#else
    if (installed) {
        installed = 0;
        remove_hooks();
    }
    enabled = 0;
#endif
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
"scout_apm.core._objtrace module.");

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

#if PY_VERSION_HEX >= 0x03050000
static int
objtrace_mod_exec(PyObject* module)
{
    PyObject *version;
    version = PyUnicode_FromString(VERSION);
    if (version == NULL)
        return -1;

    return PyModule_AddObject(module, "__version__", version);
}

static PyModuleDef_Slot _objtrace_slots[] = {
    {Py_mod_exec, objtrace_mod_exec},
    {0, NULL}
};
#endif

static struct PyModuleDef _objtrace_module = {
    PyModuleDef_HEAD_INIT,
    "scout_apm.core._objtrace",
    module_doc,
#if PY_VERSION_HEX >= 0x03050000
    sizeof(_objtrace_config_state), /* non-negative size to be able to unload the module */
#else
    0,
#endif
    module_methods,
#if PY_VERSION_HEX >= 0x03050000
    _objtrace_slots,
#else
    NULL,
#endif
    NULL,
    NULL,
    NULL
};

PyMODINIT_FUNC
PyInit__objtrace(void)
{
#if PY_VERSION_HEX >= 0x03050000
    return PyModuleDef_Init(&_objtrace_module);
#else
    PyObject *m, *version;

    m = PyModule_Create(&_objtrace_module);
    if (m == NULL)
        return NULL;

    version = PyUnicode_FromString(VERSION);
    if (version == NULL)
        return NULL;

    PyModule_AddObject(m, "__version__", version);
    return m;
#endif
}
