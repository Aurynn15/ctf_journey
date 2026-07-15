#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_NAME 96
#define MAX_INGREDIENT 32

void secret_recipe(void) {
    char buf[256];
    FILE *f = fopen("/flag.txt", "r");
    if (f) {
        if (fgets(buf, sizeof(buf), f)) {
            printf("\n");
            printf("  *** SECRET RECIPE UNLOCKED ***\n");
            printf("  The legendary smoothie ingredient is...\n");
            printf("  %s\n", buf);
        }
        fclose(f);
    }
    f = fopen("/proof.txt", "r");
    if (f) {
        if (fgets(buf, sizeof(buf), f)) {
            printf("  Unlock proof: %s\n", buf);
        }
        fclose(f);
    }
    fflush(stdout);
}

void menu(void) {
    printf("\n");
    printf("  +-----------------------------+\n");
    printf("  |    SMOOTHIE SHOP v1.0       |\n");
    printf("  +-----------------------------+\n");
    printf("  |  1. Order a smoothie        |\n");
    printf("  |  2. View today's menu       |\n");
    printf("  |  3. Exit                    |\n");
    printf("  +-----------------------------+\n");
    printf("  > ");
    fflush(stdout);
}

void order_smoothie(void) {
    char name[MAX_NAME];
    char ingredient[MAX_INGREDIENT];

    printf("\n");
    printf("  Welcome to Smoothie Shop!\n");
    printf("  We make the freshest smoothies in town.\n\n");
    printf("  What's your name? ");
    fflush(stdout);

    if (!fgets(name, sizeof(name), stdin)) return;
    name[strcspn(name, "\n")] = 0;
    name[strcspn(name, "\r")] = 0;

    printf("  Choose your ingredient: ");
    fflush(stdout);
    if (!fgets(ingredient, sizeof(ingredient), stdin)) return;
    ingredient[strcspn(ingredient, "\n")] = 0;
    ingredient[strcspn(ingredient, "\r")] = 0;

    printf("\n");
    printf("  ----------------------------------------\n");
    printf("  Preparing your order...\n");
    printf("  Thanks, ");
    printf(name);
    printf("!\n");
    printf("  One %s smoothie coming right up!\n", ingredient);
    printf("  ----------------------------------------\n");
    fflush(stdout);
}

void show_menu(void) {
    printf("\n");
    printf("  Today's Specials:\n");
    printf("  ------------------\n");
    printf("  Mango Tango ......... $5\n");
    printf("  Berry Blast ......... $6\n");
    printf("  Green Machine ....... $7\n");
    printf("  Tropical Sunrise .... $8\n");
    printf("  Protein Power ....... $9\n");
    printf("\n");
    printf("  * Secret recipes available for staff only *\n");
    printf("  * Try the special code to unlock VIP access *\n");
    fflush(stdout);
}

int main(void) {
    char buf[16];
    while (1) {
        menu();
        if (!fgets(buf, sizeof(buf), stdin)) break;

        int choice = atoi(buf);
        switch (choice) {
            case 1:
                order_smoothie();
                break;
            case 2:
                show_menu();
                break;
            case 3:
                printf("\n  Thanks for visiting Smoothie Shop!\n");
                printf("  Come back soon!\n");
                fflush(stdout);
                return 0;
            default:
                printf("\n  Sorry, that's not on the menu.\n");
                printf("  Please choose 1, 2, or 3.\n");
                fflush(stdout);
        }
    }
    return 0;
}
