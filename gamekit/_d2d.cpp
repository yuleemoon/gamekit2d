// gamekit/_d2d.cpp - Direct2D hardware-accelerated rendering backend.

#define WIN32_LEAN_AND_MEAN
#include <Python.h>
#include <windows.h>
#include <d2d1.h>
#include <math.h>

static ID2D1Factory *g_factory = NULL;
static ID2D1HwndRenderTarget *g_rt = NULL;
static ID2D1SolidColorBrush *g_brush = NULL;
static HWND g_hwnd = NULL;

// Path geometry for batched rectangle submission.
static ID2D1PathGeometry *g_path = NULL;
static ID2D1GeometrySink *g_sink = NULL;

// Sprite array: C-side managed, rendered in one loop.
typedef struct {
    float x, y, w, h;
    float r, g, b, a;
    int visible;
} D2DSprite;

static D2DSprite *g_sprites = NULL;
static Py_ssize_t g_sprite_count = 0;
static Py_ssize_t g_sprite_cap = 0;

static PyObject *d2d_init(PyObject *self, PyObject *args)
{
    uintptr_t hwnd;
    if (!PyArg_ParseTuple(args, "k", &hwnd)) {
        return NULL;
    }
    g_hwnd = (HWND)hwnd;

    CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);

    HRESULT hr = D2D1CreateFactory(
        D2D1_FACTORY_TYPE_SINGLE_THREADED,
        &g_factory);
    if (FAILED(hr)) {
        PyErr_SetFromWindowsErr((DWORD)hr);
        return NULL;
    }

    D2D1_RENDER_TARGET_PROPERTIES rtProps = {};
    rtProps.type = D2D1_RENDER_TARGET_TYPE_DEFAULT;
    rtProps.pixelFormat.format = DXGI_FORMAT_B8G8R8A8_UNORM;
    rtProps.pixelFormat.alphaMode = D2D1_ALPHA_MODE_UNKNOWN;
    rtProps.dpiX = 96.0f;
    rtProps.dpiY = 96.0f;

    RECT rc;
    GetClientRect(g_hwnd, &rc);

    D2D1_HWND_RENDER_TARGET_PROPERTIES hwndProps = {};
    hwndProps.hwnd = g_hwnd;
    hwndProps.pixelSize.width = rc.right - rc.left;
    hwndProps.pixelSize.height = rc.bottom - rc.top;
    hwndProps.presentOptions = D2D1_PRESENT_OPTIONS_IMMEDIATELY;

    hr = g_factory->CreateHwndRenderTarget(&rtProps, &hwndProps, &g_rt);
    if (FAILED(hr)) {
        PyErr_SetFromWindowsErr((DWORD)hr);
        return NULL;
    }

    D2D1_COLOR_F red = {1.0f, 0.0f, 0.0f, 1.0f};
    hr = g_rt->CreateSolidColorBrush(red, &g_brush);
    if (FAILED(hr)) {
        PyErr_SetFromWindowsErr((DWORD)hr);
        return NULL;
    }

    // Create path geometry for batched rectangle rendering.
    hr = g_factory->CreatePathGeometry(&g_path);
    if (FAILED(hr)) {
        PyErr_SetFromWindowsErr((DWORD)hr);
        return NULL;
    }

    Py_RETURN_NONE;
}

static PyObject *d2d_begin(PyObject *self, PyObject *args)
{
    float r, g, b, a;
    if (!PyArg_ParseTuple(args, "ffff", &r, &g, &b, &a)) {
        return NULL;
    }
    g_rt->BeginDraw();
    D2D1_COLOR_F clearColor = {r, g, b, a};
    g_rt->Clear(clearColor);
    Py_RETURN_NONE;
}

static PyObject *d2d_fill_rect(PyObject *self, PyObject *args)
{
    float x, y, w, h, r, g, b, a;
    if (!PyArg_ParseTuple(args, "ffffffff", &x, &y, &w, &h,
                          &r, &g, &b, &a)) {
        return NULL;
    }
    D2D1_COLOR_F color = {r, g, b, a};
    g_brush->SetColor(color);
    D2D1_RECT_F rect = {x, y, x + w, y + h};
    g_rt->FillRectangle(rect, g_brush);
    Py_RETURN_NONE;
}

static PyObject *d2d_fill_ellipse(PyObject *self, PyObject *args)
{
    float cx, cy, rx, ry, r, g, b, a;
    if (!PyArg_ParseTuple(args, "ffffffff",
                          &cx, &cy, &rx, &ry, &r, &g, &b, &a)) {
        return NULL;
    }
    D2D1_COLOR_F color = {r, g, b, a};
    g_brush->SetColor(color);
    D2D1_ELLIPSE ellipse = {{cx, cy}, rx, ry};
    g_rt->FillEllipse(ellipse, g_brush);
    Py_RETURN_NONE;
}

static PyObject *d2d_draw_line(PyObject *self, PyObject *args)
{
    float x1, y1, x2, y2, r, g, b, a, width;
    if (!PyArg_ParseTuple(args, "fffffffff",
                          &x1, &y1, &x2, &y2, &r, &g, &b, &a, &width)) {
        return NULL;
    }
    D2D1_COLOR_F color = {r, g, b, a};
    g_brush->SetColor(color);
    D2D1_POINT_2F p1 = {x1, y1};
    D2D1_POINT_2F p2 = {x2, y2};
    g_rt->DrawLine(p1, p2, g_brush, width);
    Py_RETURN_NONE;
}

static PyObject *d2d_fill_polygon(PyObject *self, PyObject *args)
{
    PyObject *pts_obj;
    float r, g, b, a;
    if (!PyArg_ParseTuple(args, "Offff", &pts_obj, &r, &g, &b, &a)) {
        return NULL;
    }
    PyObject *pts = PySequence_Fast(pts_obj, "expected points");
    if (!pts) return NULL;
    Py_ssize_t n = PySequence_Fast_GET_SIZE(pts) / 2;
    if (n < 3) { Py_DECREF(pts); Py_RETURN_NONE; }

    ID2D1PathGeometry *poly_path = NULL;
    g_factory->CreatePathGeometry(&poly_path);
    ID2D1GeometrySink *sink = NULL;
    poly_path->Open(&sink);

    D2D1_COLOR_F color = {r, g, b, a};
    g_brush->SetColor(color);

    PyObject **items = PySequence_Fast_ITEMS(pts);
    D2D1_POINT_2F first = {(float)PyFloat_AsDouble(items[0]),
                           (float)PyFloat_AsDouble(items[1])};
    sink->BeginFigure(first, D2D1_FIGURE_BEGIN_FILLED);
    for (Py_ssize_t i = 1; i < n; i++) {
        D2D1_POINT_2F p = {(float)PyFloat_AsDouble(items[i*2]),
                          (float)PyFloat_AsDouble(items[i*2+1])};
        sink->AddLine(p);
    }
    sink->EndFigure(D2D1_FIGURE_END_CLOSED);
    sink->Close();
    g_rt->FillGeometry(poly_path, g_brush);
    sink->Release();
    poly_path->Release();
    Py_DECREF(pts);
    Py_RETURN_NONE;
}

static PyObject *d2d_fill_arc(PyObject *self, PyObject *args)
{
    float x1, y1, x2, y2, start, extent, r, g, b, a;
    if (!PyArg_ParseTuple(args, "ffffffffffff",
                          &x1, &y1, &x2, &y2, &start, &extent,
                          &r, &g, &b, &a)) {
        return NULL;
    }
    ID2D1PathGeometry *arc_path = NULL;
    g_factory->CreatePathGeometry(&arc_path);
    ID2D1GeometrySink *sink = NULL;
    arc_path->Open(&sink);

    D2D1_COLOR_F color = {r, g, b, a};
    g_brush->SetColor(color);

    float cx = (x1 + x2) / 2.0f;
    float cy = (y1 + y2) / 2.0f;
    float rx = (x2 - x1) / 2.0f;
    float ry = (y2 - y1) / 2.0f;

    D2D1_POINT_2F center = {cx, cy};
    sink->BeginFigure(center, D2D1_FIGURE_BEGIN_FILLED);

    float start_rad = start * 3.14159265f / 180.0f;
    float end_rad = (start + extent) * 3.14159265f / 180.0f;
    D2D1_POINT_2F start_pt = {
        cx + rx * cosf(start_rad),
        cy + ry * sinf(start_rad)
    };
    sink->AddLine(start_pt);

    D2D1_ARC_SEGMENT arc = {};
    arc.point = {cx + rx * cosf(end_rad), cy + ry * sinf(end_rad)};
    arc.size = {rx, ry};
    arc.rotationAngle = 0.0f;
    arc.sweepDirection = (extent >= 0) ? D2D1_SWEEP_DIRECTION_CLOCKWISE
                                       : D2D1_SWEEP_DIRECTION_COUNTER_CLOCKWISE;
    arc.arcSize = D2D1_ARC_SIZE_SMALL;
    sink->AddArc(arc);
    sink->EndFigure(D2D1_FIGURE_END_CLOSED);
    sink->Close();
    g_rt->FillGeometry(arc_path, g_brush);
    sink->Release();
    arc_path->Release();
    Py_RETURN_NONE;
}

static PyObject *d2d_end(PyObject *self, PyObject *args)
{
    HRESULT hr = g_rt->EndDraw(NULL, NULL);
    return PyLong_FromLong((long)hr);
}

// batch_fill: read float buffer directly via buffer protocol.
// Buffer layout: N * 8 floats [x1,y1,w1,h1,r1,g1,b1,a1, ...]
// Avoids per-element PyObject overhead.
static PyObject *d2d_batch_fill(PyObject *self, PyObject *args)
{
    PyObject *buf_obj;
    if (!PyArg_ParseTuple(args, "O", &buf_obj)) {
        return NULL;
    }
    Py_buffer view;
    if (PyObject_GetBuffer(buf_obj, &view, PyBUF_CONTIG_RO) < 0) {
        return NULL;
    }
    Py_ssize_t n_floats = view.len / (Py_ssize_t)sizeof(float);
    Py_ssize_t groups = n_floats / 8;
    const float *data = (const float *)view.buf;
    for (Py_ssize_t i = 0; i < groups; i++) {
        float x = data[i*8+0];
        float y = data[i*8+1];
        float w = data[i*8+2];
        float h = data[i*8+3];
        float r = data[i*8+4];
        float g = data[i*8+5];
        float b = data[i*8+6];
        float a = data[i*8+7];
        D2D1_COLOR_F color = {r, g, b, a};
        g_brush->SetColor(color);
        D2D1_RECT_F rect = {x, y, x + w, y + h};
        g_rt->FillRectangle(rect, g_brush);
    }
    PyBuffer_Release(&view);
    Py_RETURN_NONE;
}

// ---- Sprite array management ----

static PyObject *d2d_add_sprite(PyObject *self, PyObject *args)
{
    float x, y, w, h, r, g, b, a;
    if (!PyArg_ParseTuple(args, "ffffffff",
                          &x, &y, &w, &h, &r, &g, &b, &a)) {
        return NULL;
    }
    if (g_sprite_count >= g_sprite_cap) {
        g_sprite_cap = g_sprite_cap ? g_sprite_cap * 2 : 256;
        g_sprites = (D2DSprite *)realloc(g_sprites,
                                         g_sprite_cap * sizeof(D2DSprite));
        if (!g_sprites) {
            return PyErr_NoMemory();
        }
    }
    D2DSprite *s = &g_sprites[g_sprite_count];
    // Quantize color to 4 bits per channel (16 levels) to reduce unique colors.
    s->x = x; s->y = y; s->w = w; s->h = h;
    s->r = roundf(r * 3.0f) / 3.0f;
    s->g = roundf(g * 3.0f) / 3.0f;
    s->b = roundf(b * 3.0f) / 3.0f;
    s->a = a;
    s->visible = 1;
    return PyLong_FromLong((long)g_sprite_count++);
}

static PyObject *d2d_set_pos(PyObject *self, PyObject *args)
{
    long idx; float x, y;
    if (!PyArg_ParseTuple(args, "lff", &idx, &x, &y)) {
        return NULL;
    }
    if (idx < 0 || idx >= g_sprite_count) {
        PyErr_SetString(PyExc_IndexError, "sprite index out of range");
        return NULL;
    }
    g_sprites[idx].x = x;
    g_sprites[idx].y = y;
    Py_RETURN_NONE;
}

static PyObject *d2d_set_color(PyObject *self, PyObject *args)
{
    long idx; float r, g, b, a;
    if (!PyArg_ParseTuple(args, "lffff", &idx, &r, &g, &b, &a)) {
        return NULL;
    }
    if (idx < 0 || idx >= g_sprite_count) {
        PyErr_SetString(PyExc_IndexError, "sprite index out of range");
        return NULL;
    }
    g_sprites[idx].r = r;
    g_sprites[idx].g = g;
    g_sprites[idx].b = b;
    g_sprites[idx].a = a;
    Py_RETURN_NONE;
}

static PyObject *d2d_set_visible(PyObject *self, PyObject *args)
{
    long idx; int vis;
    if (!PyArg_ParseTuple(args, "li", &idx, &vis)) {
        return NULL;
    }
    if (idx < 0 || idx >= g_sprite_count) {
        PyErr_SetString(PyExc_IndexError, "sprite index out of range");
        return NULL;
    }
    g_sprites[idx].visible = vis;
    Py_RETURN_NONE;
}

// Sort sprites by color so same-color sprites are contiguous.
// Reduces SetColor calls from N to (# unique colors).
static int _cmp_color(const void *a, const void *b)
{
    const D2DSprite *sa = (const D2DSprite *)a;
    const D2DSprite *sb = (const D2DSprite *)b;
    if (sa->r != sb->r) return (sa->r < sb->r) ? -1 : 1;
    if (sa->g != sb->g) return (sa->g < sb->g) ? -1 : 1;
    if (sa->b != sb->b) return (sa->b < sb->b) ? -1 : 1;
    return 0;
}

static PyObject *d2d_sort_sprites(PyObject *self, PyObject *args)
{
    if (g_sprites && g_sprite_count > 1) {
        qsort(g_sprites, g_sprite_count, sizeof(D2DSprite), _cmp_color);
    }
    Py_RETURN_NONE;
}

static PyObject *d2d_render_sprites(PyObject *self, PyObject *args)
{
    float ox, oy;
    if (!PyArg_ParseTuple(args, "ff", &ox, &oy)) {
        return NULL;
    }
    float last_r = -1.0f, last_g = -1.0f, last_b = -1.0f, last_a = -1.0f;
    for (Py_ssize_t i = 0; i < g_sprite_count; i++) {
        D2DSprite *s = &g_sprites[i];
        if (!s->visible) continue;
        // Only SetColor when color changes (avoid redundant GPU state switches)
        if (s->r != last_r || s->g != last_g ||
            s->b != last_b || s->a != last_a) {
            D2D1_COLOR_F color = {s->r, s->g, s->b, s->a};
            g_brush->SetColor(color);
            last_r = s->r; last_g = s->g;
            last_b = s->b; last_a = s->a;
        }
        D2D1_RECT_F rect = {s->x - ox, s->y - oy,
                            s->x - ox + s->w, s->y - oy + s->h};
        g_rt->FillRectangle(rect, g_brush);
    }
    Py_RETURN_NONE;
}

// Batched render: group sprites by color, build one PathGeometry per color,
// one FillGeometry call per color group. Reuse pre-created path geometry.
static PyObject *d2d_render_batched(PyObject *self, PyObject *args)
{
    float ox, oy;
    if (!PyArg_ParseTuple(args, "ff", &ox, &oy)) {
        return NULL;
    }

    // Sprites are pre-sorted by color. Walk through runs of same color.
    Py_ssize_t i = 0;
    while (i < g_sprite_count) {
        D2DSprite *s = &g_sprites[i];
        if (!s->visible) { i++; continue; }

        // Find run of same color
        float cr = s->r, cg = s->g, cb = s->b, ca = s->a;
        Py_ssize_t start = i;
        while (i < g_sprite_count) {
            D2DSprite *t = &g_sprites[i];
            if (!t->visible) { i++; continue; }
            if (t->r != cr || t->g != cg || t->b != cb || t->a != ca) break;
            i++;
        }

        // Build path for this color run
        ID2D1GeometrySink *sink = NULL;
        HRESULT hr = g_path->Open(&sink);
        if (FAILED(hr)) continue;

        D2D1_COLOR_F color = {cr, cg, cb, ca};
        g_brush->SetColor(color);

        for (Py_ssize_t j = start; j < i; j++) {
            D2DSprite *sp = &g_sprites[j];
            if (!sp->visible) continue;
            float x = sp->x - ox;
            float y = sp->y - oy;
            D2D1_POINT_2F pts[4] = {
                {x, y},
                {x + sp->w, y},
                {x + sp->w, y + sp->h},
                {x, y + sp->h}
            };
            sink->BeginFigure(pts[0], D2D1_FIGURE_BEGIN_FILLED);
            sink->AddLines(pts + 1, 3);
            sink->EndFigure(D2D1_FIGURE_END_CLOSED);
        }

        sink->Close();
        g_rt->FillGeometry(g_path, g_brush);
        sink->Release();

        // Reset path for next group (reopen, no recreate)
        g_path->Release();
        hr = g_factory->CreatePathGeometry(&g_path);
        if (FAILED(hr)) break;
    }

    Py_RETURN_NONE;
}

static PyObject *d2d_clear_sprites(PyObject *self, PyObject *args)
{
    g_sprite_count = 0;
    Py_RETURN_NONE;
}

// Per-frame batch buffer: all rects collected in C, rendered in one shot.
static float *g_batch_buf = NULL;
static Py_ssize_t g_batch_count = 0;
static Py_ssize_t g_batch_cap = 0;

// Persistent sprite array: created once, updated per-frame.
typedef struct {
    float x, y, w, h;
    float r, g, b, a;
    int visible;
} D2DPersistSprite;

static D2DPersistSprite *g_psprites = NULL;
static Py_ssize_t g_psprite_count = 0;
static Py_ssize_t g_psprite_cap = 0;

static PyObject *d2d_register_sprite(PyObject *self, PyObject *args)
{
    float x, y, w, h, r, g, b, a;
    if (!PyArg_ParseTuple(args, "ffffffff", &x, &y, &w, &h,
                          &r, &g, &b, &a)) {
        return NULL;
    }
    if (g_psprite_count >= g_psprite_cap) {
        g_psprite_cap = (g_psprite_cap + 1024) * 2;
        g_psprites = (D2DPersistSprite *)realloc(g_psprites,
                     g_psprite_cap * sizeof(D2DPersistSprite));
    }
    Py_ssize_t idx = g_psprite_count;
    D2DPersistSprite *s = &g_psprites[idx];
    s->x = x; s->y = y; s->w = w; s->h = h;
    s->r = roundf(r * 3.0f) / 3.0f;
    s->g = roundf(g * 3.0f) / 3.0f;
    s->b = roundf(b * 3.0f) / 3.0f;
    s->a = a;
    s->visible = 1;
    g_psprite_count++;
    return PyLong_FromLong((long)idx);
}

static PyObject *d2d_set_sprite_pos(PyObject *self, PyObject *args)
{
    long idx;
    float x, y;
    if (!PyArg_ParseTuple(args, "lff", &idx, &x, &y)) {
        return NULL;
    }
    if (idx >= 0 && idx < g_psprite_count) {
        g_psprites[idx].x = x;
        g_psprites[idx].y = y;
    }
    Py_RETURN_NONE;
}

static PyObject *d2d_set_sprite_visible(PyObject *self, PyObject *args)
{
    long idx;
    int vis;
    if (!PyArg_ParseTuple(args, "li", &idx, &vis)) {
        return NULL;
    }
    if (idx >= 0 && idx < g_psprite_count) {
        g_psprites[idx].visible = vis;
    }
    Py_RETURN_NONE;
}

static PyObject *d2d_render_psprites(PyObject *self, PyObject *args)
{
    float last_r = -1.0f, last_g = -1.0f, last_b = -1.0f;
    for (Py_ssize_t i = 0; i < g_psprite_count; i++) {
        D2DPersistSprite *s = &g_psprites[i];
        if (!s->visible) continue;
        if (s->r != last_r || s->g != last_g || s->b != last_b) {
            D2D1_COLOR_F color = {s->r, s->g, s->b, s->a};
            g_brush->SetColor(color);
            last_r = s->r; last_g = s->g; last_b = s->b;
        }
        D2D1_RECT_F rect = {s->x, s->y, s->x + s->w, s->y + s->h};
        g_rt->FillRectangle(rect, g_brush);
    }
    Py_RETURN_NONE;
}

static PyObject *d2d_clear_psprites(PyObject *self, PyObject *args)
{
    g_psprite_count = 0;
    Py_RETURN_NONE;
}

// Batch update all sprite positions from a flat float buffer (2 floats per sprite).
static PyObject *d2d_update_positions(PyObject *self, PyObject *args)
{
    PyObject *buf_obj;
    if (!PyArg_ParseTuple(args, "O", &buf_obj)) {
        return NULL;
    }
    Py_buffer view;
    if (PyObject_GetBuffer(buf_obj, &view, PyBUF_CONTIG_RO) < 0) {
        return NULL;
    }
    const float *data = (const float *)view.buf;
    Py_ssize_t n = view.len / (Py_ssize_t)sizeof(float) / 2;
    if (n > g_psprite_count) n = g_psprite_count;
    for (Py_ssize_t i = 0; i < n; i++) {
        g_psprites[i].x = data[i*2+0];
        g_psprites[i].y = data[i*2+1];
    }
    PyBuffer_Release(&view);
    Py_RETURN_NONE;
}

static PyObject *d2d_push_rect(PyObject *self, PyObject *args)
{
    float x, y, w, h, r, g, b, a;
    if (!PyArg_ParseTuple(args, "ffffffff", &x, &y, &w, &h,
                          &r, &g, &b, &a)) {
        return NULL;
    }
    if (g_batch_count >= g_batch_cap) {
        g_batch_cap = (g_batch_cap + 2048) * 2;
        g_batch_buf = (float *)realloc(g_batch_buf,
                                       g_batch_cap * 8 * sizeof(float));
    }
    float *p = &g_batch_buf[g_batch_count * 8];
    p[0] = x; p[1] = y; p[2] = w; p[3] = h;
    p[4] = roundf(r * 3.0f) / 3.0f;
    p[5] = roundf(g * 3.0f) / 3.0f;
    p[6] = roundf(b * 3.0f) / 3.0f;
    p[7] = a;
    g_batch_count++;
    Py_RETURN_NONE;
}

static PyObject *d2d_render_batch(PyObject *self, PyObject *args)
{
    for (Py_ssize_t i = 0; i < g_batch_count; i++) {
        float *p = &g_batch_buf[i * 8];
        D2D1_COLOR_F color = {p[4], p[5], p[6], p[7]};
        g_brush->SetColor(color);
        D2D1_RECT_F rect = {p[0], p[1], p[0] + p[2], p[1] + p[3]};
        g_rt->FillRectangle(rect, g_brush);
    }
    g_batch_count = 0;
    Py_RETURN_NONE;
}

static PyObject *d2d_clear_batch(PyObject *self, PyObject *args)
{
    g_batch_count = 0;
    Py_RETURN_NONE;
}
// Avoids 4000 individual Python->C calls per frame.
static PyObject *d2d_add_sprites_batch(PyObject *self, PyObject *args)
{
    PyObject *buf_obj;
    if (!PyArg_ParseTuple(args, "O", &buf_obj)) {
        return NULL;
    }
    Py_buffer view;
    if (PyObject_GetBuffer(buf_obj, &view, PyBUF_CONTIG_RO) < 0) {
        return NULL;
    }
    Py_ssize_t n_floats = view.len / (Py_ssize_t)sizeof(float);
    Py_ssize_t n = n_floats / 8;
    const float *data = (const float *)view.buf;

    // Ensure capacity
    Py_ssize_t needed = g_sprite_count + n;
    if (needed > g_sprite_cap) {
        g_sprite_cap = needed * 2;
        g_sprites = (D2DSprite *)realloc(g_sprites,
                                         g_sprite_cap * sizeof(D2DSprite));
        if (!g_sprites) {
            PyBuffer_Release(&view);
            return PyErr_NoMemory();
        }
    }
    for (Py_ssize_t i = 0; i < n; i++) {
        D2DSprite *s = &g_sprites[g_sprite_count + i];
        s->x = data[i*8+0];
        s->y = data[i*8+1];
        s->w = data[i*8+2];
        s->h = data[i*8+3];
        // Quantize color to 2 bits per channel (64 colors) to reduce
        // unique color count and SetColor switches.
        s->r = roundf(data[i*8+4] * 3.0f) / 3.0f;
        s->g = roundf(data[i*8+5] * 3.0f) / 3.0f;
        s->b = roundf(data[i*8+6] * 3.0f) / 3.0f;
        s->a = data[i*8+7];
        s->visible = 1;
    }
    g_sprite_count += n;
    PyBuffer_Release(&view);
    Py_RETURN_NONE;
}

static PyObject *d2d_shutdown(PyObject *self, PyObject *args)
{
    free(g_sprites);
    g_sprites = NULL;
    g_sprite_count = 0;
    g_sprite_cap = 0;
    if (g_brush) { g_brush->Release(); g_brush = NULL; }
    if (g_rt) { g_rt->Release(); g_rt = NULL; }
    if (g_factory) { g_factory->Release(); g_factory = NULL; }
    CoUninitialize();
    Py_RETURN_NONE;
}

static PyObject *d2d_resize(PyObject *self, PyObject *args)
{
    UINT w, h;
    if (!PyArg_ParseTuple(args, "II", &w, &h)) {
        return NULL;
    }
    if (g_rt) {
        D2D1_SIZE_U size = {w, h};
        g_rt->Resize(size);
    }
    Py_RETURN_NONE;
}

static PyMethodDef d2d_methods[] = {
    {"init", d2d_init, METH_VARARGS, "init(hwnd)"},
    {"begin", d2d_begin, METH_VARARGS, "begin(r,g,b,a)"},
    {"fill_rect", d2d_fill_rect, METH_VARARGS,
     "fill_rect(x,y,w,h,r,g,b,a)"},
    {"fill_ellipse", d2d_fill_ellipse, METH_VARARGS,
     "fill_ellipse(cx,cy,rx,ry,r,g,b,a)"},
    {"draw_line", d2d_draw_line, METH_VARARGS,
     "draw_line(x1,y1,x2,y2,r,g,b,a,width)"},
    {"fill_polygon", d2d_fill_polygon, METH_VARARGS,
     "fill_polygon(flat_pts,r,g,b,a)"},
    {"fill_arc", d2d_fill_arc, METH_VARARGS,
     "fill_arc(x1,y1,x2,y2,start,extent,r,g,b,a)"},
    {"batch_fill", d2d_batch_fill, METH_VARARGS,
     "batch_fill(flat_float_list)"},
    {"add_sprite", d2d_add_sprite, METH_VARARGS,
     "add_sprite(x,y,w,h,r,g,b,a) -> id"},
    {"set_pos", d2d_set_pos, METH_VARARGS,
     "set_pos(id,x,y)"},
    {"set_color", d2d_set_color, METH_VARARGS,
     "set_color(id,r,g,b,a)"},
    {"set_visible", d2d_set_visible, METH_VARARGS,
     "set_visible(id,visible)"},
    {"render_sprites", d2d_render_sprites, METH_VARARGS,
     "render_sprites(ox,oy)"},
    {"render_batched", d2d_render_batched, METH_VARARGS,
     "render_batched(ox,oy) - batched by color"},
    {"clear_sprites", d2d_clear_sprites, METH_VARARGS,
     "clear_sprites()"},
    {"add_sprites_batch", d2d_add_sprites_batch, METH_VARARGS,
     "add_sprites_batch(float_buffer)"},
    {"push_rect", d2d_push_rect, METH_VARARGS,
     "push_rect(x,y,w,h,r,g,b,a)"},
    {"render_batch", d2d_render_batch, METH_VARARGS,
     "render_batch()"},
    {"clear_batch", d2d_clear_batch, METH_VARARGS,
     "clear_batch()"},
    {"register_sprite", d2d_register_sprite, METH_VARARGS,
     "register_sprite(x,y,w,h,r,g,b,a) -> idx"},
    {"set_sprite_pos", d2d_set_sprite_pos, METH_VARARGS,
     "set_sprite_pos(idx,x,y)"},
    {"set_sprite_visible", d2d_set_sprite_visible, METH_VARARGS,
     "set_sprite_visible(idx,vis)"},
    {"render_psprites", d2d_render_psprites, METH_VARARGS,
     "render_psprites()"},
    {"clear_psprites", d2d_clear_psprites, METH_VARARGS,
     "clear_psprites()"},
    {"update_positions", d2d_update_positions, METH_VARARGS,
     "update_positions(flat_xy_buffer)"},
    {"sort_sprites", d2d_sort_sprites, METH_VARARGS,
     "sort_sprites() - group by color"},
    {"resize", d2d_resize, METH_VARARGS,
     "resize(w,h)"},
    {"end", d2d_end, METH_VARARGS, "end() -> hr"},
    {"shutdown", d2d_shutdown, METH_VARARGS, "shutdown()"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef d2d_module = {
    PyModuleDef_HEAD_INIT,
    "_d2d",
    "Direct2D hardware-accelerated rendering",
    -1,
    d2d_methods
};

PyMODINIT_FUNC
PyInit__d2d(void)
{
    return PyModule_Create(&d2d_module);
}
