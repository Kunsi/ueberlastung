/*
	club.h - Header file for the Club class.
	
	Revision 0
	
	Notes:
			- 
			
	2018/02/28, Maya Posch
*/

#ifndef CLUB_H
#define CLUB_H


#include <Poco/Net/HTTPClientSession.h>
#include <Poco/Net/HTTPSClientSession.h>
#include <Poco/Net/SocketAddress.h>
#include <Poco/Timestamp.h>
#include <Poco/Timer.h>
#include <Poco/Mutex.h>
#include <Poco/Condition.h>
#include <Poco/Thread.h>

using namespace Poco;
using namespace Poco::Net;

#include <string>
#include <vector>
#include <map>
#include <queue>

using namespace std;

// Raspberry Pi GPIO, i2c, etc. functionality.
#include <wiringPi.h>
#include <wiringPiI2C.h>


class Listener;


class ClubUpdater : public Runnable {
	TimerCallback<ClubUpdater>* cb;
	uint8_t regDir0;
	uint8_t regOut0;
	int i2cHandle;
	Timer* timer;
	Mutex mutex;
	Mutex timerMutex;
	
public:
	void run();
	void updateStatus();
	void writeRelayOutputs();
	void setPowerState(Timer &t);
};


class Club {
	static Thread updateThread;
	static ClubUpdater updater;
	
	static void lockISRCallback();
	static void statusISRCallback();
	
public:
	static bool clubOff;
	static bool clubLocked;
	static bool powerOn;
	static Listener* mqtt;
	static bool relayActive;
	static uint8_t relayAddress;
	static string mqttTopic;	// Topic we publish status updates on.
	
	static Condition clubCnd;
	static Mutex clubCndMutex;
	static bool clubChanged ;
	static bool running;
	static bool clubIsClosed;
	
	static bool start(bool relayactive, uint8_t relayaddress, string topic);
	static void stop();
	static void togglePower();
	static void setRelay();
};

#endif
