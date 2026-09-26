#include <windows.h>
#include <d2d1.h>
#include <stdio.h>

int main() {
    CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
    ID2D1Factory *factory = NULL;
    // C++ template version: (factoryType, &factory)
    HRESULT hr = D2D1CreateFactory(D2D1_FACTORY_TYPE_SINGLE_THREADED, &factory);
    printf("hr=0x%08x factory=%p\n", hr, factory);
    if (SUCCEEDED(hr)) {
        printf("D2D1 Factory OK!\n");
        factory->Release();
    }
    CoUninitialize();
    return 0;
}
