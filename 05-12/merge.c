#include <stdlib.h>
#include <stdio.h>

int comp(const void* a, const void* b) {
    int v_a = *(int*)a;
    int v_b = *(int*)b;
    int r   = v_a - v_b;
    return r;
}

void merge(int* v_a, int s_a, int* v_b, int s_b) {
    int* original_vector = v_a;
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
    int* non_empty;
    if(s_a != 0) {
        non_empty = v_a;
    } else {
        non_empty = v_b;
    }

    while(aux_i != total_size) {
        aux[aux_i] = *non_empty;
        aux_i++;
        non_empty++;
    }

    // Copy the aux vector over the original one
    for(int i = 0; i < total_size; i++) {
        original_vector[i] = aux[i];
    }
}

int main(int argc, char** argv) {
    int a[6] = {1,4,9,2,3,5};
    int* b = a+3;

    merge(a, 3, b, 3);

    printf("%d %d %d %d %d %d\n", a[0], a[1], a[2], a[3], a[4], a[5]);
}