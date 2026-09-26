#include <windows.h>
#include <d2d1.h>
#include <stdio.h>

int main() {
    const IID *iid = &IID_ID2D1Factory;
    printf("IID bytes: ");
    for (int i = 0; i < 16; i++) {
        printf("%02x ", ((unsigned char*)iid)[i]);
    }
    printf("\n");
    return 0;
}
