// d2d_slots3.c - get exact vtable indices via member function pointers
#include <windows.h>
#include <d2d1.h>
#include <stdio.h>
#pragma comment(lib, "d2d1.lib")
#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "user32.lib")

// Cast member function pointer to get the actual function address
template<typename T>
void* GetVtblEntry(T* /*obj*/, void (T::*method)()) {
    union {
        void (T::*m)();
        void* p;
    } u;
    u.m = method;
    return u.p;
}

template<typename T, typename A1>
void* GetVtblEntry1(T* obj, void (T::*method)(A1)) {
    union {
        void (T::*m)(A1);
        void* p;
    } u;
    u.m = method;
    return u.p;
}

int main() {
    CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
    ID2D1Factory *factory = NULL;
    D2D1CreateFactory(D2D1_FACTORY_TYPE_SINGLE_THREADED, &factory);
    HWND hwnd = CreateWindowExW(0, L"STATIC", L"", 0,0,0,1,1, NULL,NULL,NULL,NULL);
    D2D1_RENDER_TARGET_PROPERTIES p = {};
    p.pixelFormat.format = DXGI_FORMAT_B8G8R8A8_UNORM;
    p.pixelFormat.alphaMode = D2D1_ALPHA_MODE_UNKNOWN;
    D2D1_HWND_RENDER_TARGET_PROPERTIES hp = {};
    hp.hwnd = hwnd; hp.pixelSize.width = 800; hp.pixelSize.height = 600;
    ID2D1HwndRenderTarget *rt = NULL;
    factory->CreateHwndRenderTarget(&p, &hp, &rt);
    if (rt) {
        void **vt = *(void***)rt;

        // Get BeginDraw address
        void* bd = GetVtblEntry1(rt, &ID2D1RenderTarget::BeginDraw);
        // Get Clear address
        void* cl = GetVtblEntry1(rt, &ID2D1RenderTarget::Clear);
        // Get EndDraw address
        void* ed = GetVtblEntry1(rt, &ID2D1RenderTarget::EndDraw);

        printf("BeginDraw = %p\n", bd);
        printf("Clear     = %p\n", cl);
        printf("EndDraw   = %p\n", ed);

        // Find their indices
        for (int i = 0; i < 60; i++) {
            if (vt[i] == bd) printf("  -> BeginDraw at slot %d\n", i);
            if (vt[i] == cl) printf("  -> Clear at slot %d\n", i);
            if (vt[i] == ed) printf("  -> EndDraw at slot %d\n", i);
        }
        rt->Release();
    }
    factory->Release();
    CoUninitialize();
    return 0;
}
