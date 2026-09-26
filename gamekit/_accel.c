/* gamekit/_accel.c - batch BitBlt C extension. */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <windows.h>
#include <stdlib.h>

/* ---- 精灵数组：C 层直接遍历 blit，完全跳过 Python 循环 ---- */
typedef struct {
    int x, y, w, h;
    HDC src_dc;
    int visible;
} SpriteItem;

static SpriteItem *g_items = NULL;
static int g_count = 0;
static int g_cap = 0;

static PyObject *
batch_register(PyObject *self, PyObject *args)
{
    int x, y, w, h;
    HDC src_dc;
    if (!PyArg_ParseTuple(args, "iiiik", &x, &y, &w, &h, &src_dc)) {
        return NULL;
    }
    if (g_count >= g_cap) {
        g_cap = g_cap ? g_cap * 2 : 1024;
        g_items = (SpriteItem *)realloc(g_items, g_cap * sizeof(SpriteItem));
    }
    int idx = g_count++;
    g_items[idx].x = x; g_items[idx].y = y;
    g_items[idx].w = w; g_items[idx].h = h;
    g_items[idx].src_dc = src_dc;
    g_items[idx].visible = 1;
    return PyLong_FromLong(idx);
}

static PyObject *
batch_set_pos(PyObject *self, PyObject *args)
{
    int idx, x, y;
    if (!PyArg_ParseTuple(args, "iii", &idx, &x, &y)) {
        return NULL;
    }
    if (idx >= 0 && idx < g_count) {
        g_items[idx].x = x;
        g_items[idx].y = y;
    }
    Py_RETURN_NONE;
}

static PyObject *
batch_set_visible(PyObject *self, PyObject *args)
{
    int idx, v;
    if (!PyArg_ParseTuple(args, "ii", &idx, &v)) {
        return NULL;
    }
    if (idx >= 0 && idx < g_count) {
        g_items[idx].visible = v;
    }
    Py_RETURN_NONE;
}

static PyObject *
batch_render(PyObject *self, PyObject *args)
{
    HDC dst_dc;
    int ox, oy;
    if (!PyArg_ParseTuple(args, "kii", &dst_dc, &ox, &oy)) {
        return NULL;
    }
    int done = 0;
    for (int i = 0; i < g_count; i++) {
        SpriteItem *s = &g_items[i];
        if (!s->visible || s->src_dc == NULL) continue;
        BitBlt(dst_dc, s->x - ox, s->y - oy, s->w, s->h,
               s->src_dc, 0, 0, SRCCOPY);
        done++;
    }
    return PyLong_FromLong(done);
}

static PyObject *
batch_reset(PyObject *self, PyObject *args)
{
    g_count = 0;
    Py_RETURN_NONE;
}

static PyObject *
batch_blit(PyObject *self, PyObject *args)
{
    HDC dst_dc;
    PyObject *items;
    if (!PyArg_ParseTuple(args, "kO", &dst_dc, &items)) {
        return NULL;
    }
    if (!PyList_Check(items)) {
        PyErr_SetString(PyExc_TypeError, "items must be a list");
        return NULL;
    }
    Py_ssize_t n = PyList_GET_SIZE(items);
    int done = 0;
    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *item = PyList_GET_ITEM(items, i);
        if (!PyTuple_Check(item) || PyTuple_GET_SIZE(item) != 5) {
            continue;
        }
        HDC src_dc = (HDC) PyLong_AsVoidPtr(PyTuple_GET_ITEM(item, 0));
        int dx = (int) PyLong_AsLong(PyTuple_GET_ITEM(item, 1));
        int dy = (int) PyLong_AsLong(PyTuple_GET_ITEM(item, 2));
        int w = (int) PyLong_AsLong(PyTuple_GET_ITEM(item, 3));
        int h = (int) PyLong_AsLong(PyTuple_GET_ITEM(item, 4));
        if (src_dc && w > 0 && h > 0) {
            BitBlt(dst_dc, dx, dy, w, h, src_dc, 0, 0, SRCCOPY);
            done++;
        }
    }
    return PyLong_FromLong(done);
}

static PyMethodDef methods[] = {
    {"batch_blit", batch_blit, METH_VARARGS,
     "batch_blit(dst_dc, items) -> int"},
    {"batch_register", batch_register, METH_VARARGS,
     "register_rect(x, y, w, h, src_dc) -> index"},
    {"batch_set_pos", batch_set_pos, METH_VARARGS,
     "set_pos(index, x, y)"},
    {"batch_set_visible", batch_set_visible, METH_VARARGS,
     "set_visible(index, v)"},
    {"batch_render", batch_render, METH_VARARGS,
     "render(dst_dc, ox, oy) -> int"},
    {"batch_reset", batch_reset, METH_VARARGS,
     "reset()"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef accel_module = {
    PyModuleDef_HEAD_INIT,
    "_accel",
    "C accelerated batch blit",
    -1,
    methods
};

PyMODINIT_FUNC
PyInit__accel(void)
{
    return PyModule_Create(&accel_module);
}

