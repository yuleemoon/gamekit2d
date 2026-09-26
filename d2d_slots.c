// d2d_slots.c - find correct vtable slots
#include <windows.h>
#include <d2d1.h>
#include <stdio.h>

#pragma comment(lib, "d2d1.lib")
#pragma comment(lib, "ole32.lib")

int main() {
    CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);

    ID2D1Factory *factory = NULL;
    D2D1CreateFactory(D2D1_FACTORY_TYPE_SINGLE_THREADED, &factory);

    HWND hwnd = CreateWindowExW(0, L"STATIC", L"", 0, 0,0,1,1, NULL, NULL, NULL, NULL);

    D2D1_RENDER_TARGET_PROPERTIES rtProps = {};
    rtProps.type = D2D1_RENDER_TARGET_TYPE_DEFAULT;
    rtProps.pixelFormat.format = DXGI_FORMAT_B8G8R8A8_UNORM;
    rtProps.pixelFormat.alphaMode = D2D1_ALPHA_MODE_UNKNOWN;
    rtProps.dpiX = 96; rtProps.dpiY = 96;

    D2D1_HWND_RENDER_TARGET_PROPERTIES hwndProps = {};
    hwndProps.hwnd = hwnd;
    hwndProps.pixelSize.width = 800;
    hwndProps.pixelSize.height = 600;

    ID2D1HwndRenderTarget *rt = NULL;
    factory->CreateHwndRenderTarget(&rtProps, &hwndProps, &rt);

    if (rt) {
        // Get vtable
        void **vt = *(void***)rt;
        printf("vtable[0]=%p (QI)\n", vt[0]);
        printf("vtable[3]=%p (GetFactory)\n", vt[3]);
        // Print all slots up to 60
        for (int i = 0; i < 60; i++) {
            printf("vt[%d] = %p\n", i, vt[i]);
        }
        rt->Release();
    }
    factory->Release();
    CoUninitialize();
    return 0;
}
