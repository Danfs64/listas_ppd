/*
 * This is sample code generated by rpcgen.
 * These are only templates and you can use them
 * as a guideline for developing your own functions.
 */

#include "miner.h"


void
prog_100(char *host)
{
	CLIENT *clnt;
	int  *result_1;
	args  gettransactionid_100_arg;
	int  *result_2;
	args  getchallenge_100_arg;
	int  *result_3;
	args  gettransactionstatus_100_arg;
	int  *result_4;
	args  getwinner_100_arg;
	TransactionInfo  *result_5;
	args  getseed_100_arg;
	int  *result_6;
	args  submitchallenge_100_arg;

#ifndef	DEBUG
	clnt = clnt_create (host, PROG, VERSAO, "udp");
	if (clnt == NULL) {
		clnt_pcreateerror (host);
		exit (1);
	}
#endif	/* DEBUG */

	result_1 = gettransactionid_100(&gettransactionid_100_arg, clnt);
	if (result_1 == (int *) NULL) {
		clnt_perror (clnt, "call failed");
	}
	result_2 = getchallenge_100(&getchallenge_100_arg, clnt);
	if (result_2 == (int *) NULL) {
		clnt_perror (clnt, "call failed");
	}
	result_3 = gettransactionstatus_100(&gettransactionstatus_100_arg, clnt);
	if (result_3 == (int *) NULL) {
		clnt_perror (clnt, "call failed");
	}
	result_4 = getwinner_100(&getwinner_100_arg, clnt);
	if (result_4 == (int *) NULL) {
		clnt_perror (clnt, "call failed");
	}
	result_5 = getseed_100(&getseed_100_arg, clnt);
	if (result_5 == (TransactionInfo *) NULL) {
		clnt_perror (clnt, "call failed");
	}
	result_6 = submitchallenge_100(&submitchallenge_100_arg, clnt);
	if (result_6 == (int *) NULL) {
		clnt_perror (clnt, "call failed");
	}
#ifndef	DEBUG
	clnt_destroy (clnt);
#endif	 /* DEBUG */
}


int
main (int argc, char *argv[])
{
	char *host;

	if (argc < 2) {
		printf ("usage: %s server_host\n", argv[0]);
		exit (1);
	}
	host = argv[1];
	prog_100 (host);
exit (0);
}