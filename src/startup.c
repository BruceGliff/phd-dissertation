#include <pthread.h>

extern void OnThread0();
extern void OnThread1();
// Numbers of Threads

typedef void (*Call)();
Call Calls[] = {&OnThread0, &OnThread1};

void* Start(void *arg) {
  Call* Function = (Call*)arg;
  (*Function)();
  return NULL;
}

int main() {
  int ThreadNum = sizeof(Calls) / sizeof(Call);
  pthread_t Id[ThreadNum];
  for (int Curr = 0; Curr != ThreadNum; ++Curr)
    pthread_create(&Id[Curr], NULL, Start, Calls + Curr);
  for (int Curr = 0; Curr != ThreadNum; ++Curr)
    pthread_join(Id[Curr], NULL);
}

