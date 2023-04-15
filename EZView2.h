// 32 bytes, the characters "EZView2" followed by 25 bytes of zero.
// then the following structure
{
	// size of this header
	DWORD dwSize;
	// version of this header
	DWORD dwVersion;
	// device type
	DWORD dwDevType;
	// number of data records
	DWORD dwNumRec;
	// sizeof each data record (sizeof(DATA_PACKET))
	DWORD dwRecSize;
	// data collection start time (see win32 documentation for description of FILETIME)
	FILETIME ftStart;
	// time of first data record
	FILETIME ftFirst;
} EZVIEW_HEADER2;

// followed by dwNumRec number of these
struct DATA_PACKET
{
	// Timestamp in units of .1ms for EZ-Tap, 1usec for EZ-Tap+/Pro
	DWORD time;
	BYTE type,
			// Value  Definition
			// 0      Undefined
			// 1      DTE data TX
			// 2      DCE data TX
			// 3      Data Error/Break condition
			// 4      DTE handshaking status change
			// 5      DCE handshaking status change
		data,
			// Data byte for DTE and DCE TX data events
			// Status byte for DTE and DCE Error/Break condition
			// Bit    Definition
			// 0      DTE break condition
			// 1      DTE parity error
			// 2      DTE framing error
			// 3      DCE break condition
			// 4      DCE parity error
			// 5      DCE framing error
			// Status byte for DTE handshaking events:
			// Bit    Definition
			// 0      DTE RTS signal status 1 = active
			// 1      DTE DTR signal status 1 = active
			// Status byte for DCE handshaking events:
			// Bit    Definition
			// 0      DCE CTS signal status 1 = active
			// 1      DCE DSR signal status 1 = active
			// 2      DCE CD signal status 1 = active
			// 3      DCE RI signal status 1 = active
		ctl_sigs;
			// Current handshaking/control line values, 1 = active
			// Bit    Definition
			// 0      RTS
			// 1      DTR
			// 2      CTS
			// 3      DSR
			// 4      DCD
			// 5      RI
	BYTE time_msb;
};
