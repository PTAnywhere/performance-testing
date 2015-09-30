import com.cisco.pt.ipc.events.TerminalLineEvent;
import com.cisco.pt.ipc.events.TerminalLineEventListener;
import com.cisco.pt.ipc.events.TerminalLineEventRegistry;
import com.cisco.pt.ipc.sim.Network;
import com.cisco.pt.ipc.sim.CiscoDevice;
import com.cisco.pt.ipc.sim.TerminalLine;
import com.cisco.pt.ipc.ui.IPC;
import com.cisco.pt.ipc.IPCError;
import com.cisco.pt.ipc.IPCFactory;
import com.cisco.pt.launcher.PacketTracerLauncher;
import com.cisco.pt.ptmp.ConnectionNegotiationProperties;
import com.cisco.pt.ptmp.PacketTracerSession;
import com.cisco.pt.ptmp.PacketTracerSessionFactory;
import com.cisco.pt.ptmp.impl.PacketTracerSessionFactoryImpl;


/**
 * This class allows you to check when a Packet Tracer session is up and
 * able to answer IPC requests.
 *
 * Also, it can be used to measure the average response time of the instance
 * for a predefine request.
 *
 * Note that this class depends on the ptipc library.
 * I cannot provide a version of it as its intellectual property belongs to Cisco.
 */
public class PTChecker extends PacketTracerClient {

    public PTChecker(String host, int port) {
        super(host, port);
        // "forge-pt002.kmi.open.ac.uk", 39000
        // "192.168.34.202", 39001
        // "192.168.35.2", 39000
    }

    @Override
    protected void internalRun() throws Exception {
        final IPC ipc = this.ipcFactory.getIPC();
        final Network network = this.ipcFactory.network(ipc);
        final CiscoDevice dev = (CiscoDevice) network.getDevice("MySwitch");
    }

    protected long waitUntilPTResponds(int maxWaitingSeconds) {
        // TODO
        return 0;  // In miliseconds
    }

    protected long getAverageResponseTime(int repetitions) {
        // TODO
        return 0;  // In miliseconds
    }

    public static void main(String[] args) {
        if (args.length<2) {
            System.out.println("usage: java PTChecker hostname port\n");
            System.out.println("Checks the time needed to contact a PacketTracer instance.\n");
            System.out.println("\thostname\tstring with the name of the Packet Tracer instance host.");
            System.out.println("\tport    \tan integer for the port number of the Packet Tracer instance.");
        } else {
            final PTChecker checker = new PTChecker(args[0], Integer.parseInt(args[1]));
            checker.waitUntilPTResponds(5);
            //checker.getAverageResponseTime(100);
        }
    }
}

abstract class PacketTracerClient {

  	protected Process packetTracerProcess;
  	protected PacketTracerSession packetTracerSession;
  	protected IPCFactory ipcFactory;
    final protected String hostName; // "localhost";
  	final protected int port;

    public PacketTracerClient(String hostName, int port) {
        this.hostName = hostName;
        this.port = port;
    }

  	abstract protected void internalRun() throws Exception;

    public void run() throws Exception {
    		PacketTracerSessionFactory sessionFactory = PacketTracerSessionFactoryImpl.getInstance();
    		packetTracerSession = createSession(sessionFactory);
    		ipcFactory = new IPCFactory(packetTracerSession);
    		internalRun();
    }

  	protected PacketTracerSession createSession(PacketTracerSessionFactory sessionFactory) throws Exception {
    		ConnectionNegotiationProperties negotiationProperties = getNegotiationProperties();
    		if (negotiationProperties == null) {
    			   return createDefaultSession(sessionFactory);
    		} else {
    			   return createSession(sessionFactory, negotiationProperties);
    		}
  	}

  	protected PacketTracerSession createDefaultSession(PacketTracerSessionFactory sessionFactory) throws Exception {
  		  return sessionFactory.openSession(this.hostName, port);
  	}

  	protected PacketTracerSession createSession(PacketTracerSessionFactory sessionFactory, ConnectionNegotiationProperties negotiationProperties) throws Exception {
  		  return sessionFactory.openSession(this.hostName, port, negotiationProperties);
  	}

  	protected ConnectionNegotiationProperties getNegotiationProperties() {
  		  return null;
  	}
}
