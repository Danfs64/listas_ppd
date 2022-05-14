#include <stdlib.h>
#include <stdio.h>

int comp(const void* a, const void* b) {
    int v_a = *(int*)a;
    int v_b = *(int*)b;
    int r   = v_a - v_b;
    return r;
}

void merge(int* v_a, int s_a, int* v_b, int s_b) {
    int* og_vector = v_a;
    int total_size = s_a + s_b;
    int* aux = malloc(sizeof(int)*total_size);
    int aux_i = 0;

    // Merge until someone is empty
    while((s_a > 0) && (s_b > 0)) {
        if(comp(v_a, v_b) < 0) {
            aux[aux_i] = *v_a;
            v_a++;
            s_a--;
        } else {
            aux[aux_i] = *v_b;
            v_b++;
            s_b--;
        }
        aux_i++;
    }

    // Fill the aux vector with the non-empty vector
    int* non_empty = (s_a != 0) ? v_a : v_b;

    while(aux_i != total_size) {
        aux[aux_i] = *non_empty;
        aux_i++;
        non_empty++;
    }

    // Copy the aux vector over the original one
    for(int i = 0; i < total_size; i++) {
        og_vector[i] = aux[i];
    }

    free(aux);
}

int main(int argc, char** argv) {
    if(argc != 3) exit(1);

    int k = atoi(argv[1]);
    int n = atoi(argv[2]);
    int split_size = n/k;
    int last_split_size = n - (k-1)*split_size;

    printf("Splits: %d | Tamanho do split: %d | Tamanho do último split: %d\n", k, split_size, last_split_size);

    int a[6] = {1,9,4,6,3,5};
    int* b = a+3;

    qsort(a, 3, sizeof(int), comp);
    qsort(b, 3, sizeof(int), comp);
    printf("%d %d %d %d %d %d\n", a[0], a[1], a[2], a[3], a[4], a[5]);

    merge(a, 3, b, 3);
    printf("%d %d %d %d %d %d\n", a[0], a[1], a[2], a[3], a[4], a[5]);

    return 0;
}