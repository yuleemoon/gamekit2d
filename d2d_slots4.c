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
        // Use union to extract vtable index from member function pointer
        auto bd = &ID2D1RenderTarget::BeginDraw;
        auto cl = &ID2D1RenderTarget::Clear;
        auto ed = &ID2D1RenderTarget::EndDraw;
        // In MSVC single inheritance, member function pointer IS the vtable index
        // stored as a function pointer (for virtual functions)
        printf("BeginDraw ptr: %p\n", *(void**)&bd);
        printf("Clear ptr:     %p\n", *(void**)&cl);
        printf("EndDraw ptr:   %p\n", *(void**)&ed);
        // Find slots
        for (int i = 45; i <= 58; i++) {
            printf("vt[%d] = %p\n", i, vt[i]);
        }
        rt->Release();
    }
    factory->Release();
    CoUninitialize();
    return 0;
}
