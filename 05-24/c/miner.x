struct args {
    int tid;
    int cid;
    char* seed;
};

program PROG {
    version VERSAO {
        int GETTRANSACTIONID(args) = 1;
        int GETCHALLENGE(args) = 2;
        int GETTRANSACTIONSTATUS(args) = 3;
        int GETWINNER(args) = 4;
        TransactionInfo GETSEED(args) = 5;
        int SUBMITCHALLENGE(args) = 6;
    } = 100;
} = 5555;
