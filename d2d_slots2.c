// d2d_slots2.c - find BeginDraw/Clear/EndDraw addresses
#include <windows.h>
#include <d2d1.h>
#include <stdio.h>
#pragma comment(lib, "d2d1.lib")
#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "user32.lib")

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
        // Print addresses of known methods by calling them
        // BeginDraw, Clear, EndDraw
        D2D1_COLOR_F color = {0.1f, 0.1f, 0.3f, 1.0f};
        rt->BeginDraw();
        rt->Clear(&color);
        HRESULT hr = rt->EndDraw(NULL, NULL);
        printf("EndDraw hr=0x%08x\n", hr);
        // Now find which vt entries correspond
        // We know from the C++ code: BeginDraw, Clear, EndDraw
        // Let's search by comparing: we already called them, so we know
        // Print vt[48..55] and we'll match by elimination
        for (int i = 47; i <= 55; i++) {
            printf("vt[%d] = %p\n", i, vt[i]);
        }
        rt->Release();
    }
    factory->Release();
    CoUninitialize();
    return 0;
}
