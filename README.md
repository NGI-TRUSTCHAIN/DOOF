# DOOF
DOOF (Data Ownership Orchestration Framework) is a groundbreaking project aimed at revolutionizing personal data governance and establishing the groundwork for a resilient data economy. At its core, DOOF introduces a versatile framework that promotes the development of privacy-enhancing technologies, ensuring compliance with the General Data Protection Regulation (GDPR) and Data Act, thus, enabling individuals to control their data rights effectively. The mission of DOOF is to foster trust and transparency in the digital ecosystem by providing individuals with the tools to manage their personal data easily and securely. By streamlining the deployment of user-friendly, GDPR-compliant data exchanges across various sectors, DOOF offers a practical solution for data management challenges. 

DOOF's key components include a set of software development kits (SDKs), libraries, and smart contracts. Additionally, the project features a smart-home device configuration tool and a web-based data exchange platform, which streamline complex data management for users, enhancing their engagement and facilitating adoption. One of DOOF's primary advantages is its adaptability and scalability. The project leverages APIs for swift integration into existing software ecosystems, ensuring efficient, sector-wide deployment while optimizing cost-effective system integration. With DOOF, we are laying the foundation for a resilient and transparent data economy where individuals have greater control over their data, fostering trust, regulatory compliance, and ultimately, a more user-centric and secure digital landscape.

# PROJECT OBJECTIVES AND CORE FUNCTIONALITIES 

Today control over data visibility is centralized into the hands of data sharing platforms’ owners. Rightful data owners are not actively involved in the data value chain, and this results in low trust and willingness to share data, hindering the growth of a European data market.

Within NGI TrustChain Call #2, Ecosteer has developed the Data Ownership Orchestration Framework (DOOF), a set of open SDKs, libraries and Smart Contracts that allows data owners to exercise data ownership rights – i.e. control data visibility by granularly granting and revoking it to specific purposes of usage. 

This project addresses the OC 2 challenges of users’ lack of control over personal data sharing and the consequent inability to be active players in the data economy. The DOOF deliverables allow to deploy data exchange initiatives and streamline the deployment process of PETs involved in data sharing. It decouples the layer of consent management - handled within the DOOF platform - from the physical sharing of data - handled in a secure and trustworthy way via the usage of the selected PET. 

Some of core functionalities of DOOF, delivered through the client's and the smart contract's APIs, are: 
- representation of a data source through a 'product' owned by a data owner 
- direct contact between data owners and data recipients through the smart contract
- representation of the data user's visibility requests over data through a subscription, connected to a specific purpose of usage
- possibility of data owner to granularly control the visibility of third parties for specific purposes of usage over each data they own, via grant and revoke APIs 


# PROJECT DELIVERABLES

This repository contains the DOOF components developed withing the NGI Trustchain project. The following picture depicts the architecture of DOOF. 

![DOOF architecture](./documentation/architecture_doof_github.jpg)

DOOF is a distributed platform based on an event-driven architecture. Its components (in green) and the third-party components (black) that are used for the communication between them are:
-	The DOOF Client: an HTTPS client application that consumes the services offered by DOOF back-end. It can be integrated into applications used by end-users.
-	DOOF Gateway: an HTTPS Gateway which facilitates the integration and communication between clients (front-end) and worker (back-end), by exposing RESTful APIs.
-	Work Queue: A third-party message queuing system that holds all the tasks to be processed by the first available Worker. The usage of a Work Queue allows the implementation of a competing consumers pattern, which delivers high availability and horizontal scalability as it allows to distribute the overall workload over a set of Worker Processes, local or remote. An example of a message queueing system that can be used is an AMQP broker such as RabbitMQ.
-	DOOF Worker: this is the most important component within the DOOF, as it delivers the core functionality of orchestrating different services for achieving Data Ownership, including the connection with the Intermediation Platform, i.e. a blockchain such as Alastria. The DOOF Worker processes all the tasks (available from the Work Queue) that were fed by the DOOF Gateway, based on the requests from the DOOF Client.
-	Broker: A third-party pub-sub broker that is used by the Worker to send asynchronous notifications to the DOOF Client. Typically, the asynchronous notifications originated by the Worker hold the results of the processing triggered by the requests sent by the DOOF Clients. A communication based on pub-sub broker is needed as the Intermediation Platform may expose non-deterministic latencies. A pub-sub broker may implement mqtt protocol, and be e.g. EMQX. The DOOF Client subscribes to a topic of this pub-sub broker which is specific for the client’s session, in order to receive the asynchronous notifications. The DOOF worker publishes notifications on the topic specific to the client’s session.
-	Solidity Smart Contract: The smart contract on the intermediation platform has the responsibility to maintain the relationships between Data Owners and Data Users and the list of consents that the data owner has granted to data users. The intermediation platform can be implemented in several different ways, depending on the desired degree of decentralization. For instance, the intermediation platform can be based on DLT technologies (in particular: Alastria) or on more traditional technologies like RDBMS. In case of a blockchain platform is used, the relationships between Data Owners and Data Users are maintained thanks to a set of Smart Contracts developed by Ecosteer.
-   Database: A persistence layer used to keep an off-chain representation and additional details regarding the objects found in the smart contract, for user and session management, and for any other extension that may be required by a given use case.  

The providers (in blue) are pluggable modules that adhere to a common abstract interface and handle, e.g., the communication with the third party components such as the Work Queue and the pub/sub broker.

The web front-end component (in orange) is an instance of the DOOF client that uses some of the functionalities exposed by the client's APIs. It is a component developed for the piloting phase of the DOOF, for the creation of a Web Data Exchange, which demonstrated of the capabilities and functionalities of DOOF. This exchange is made available to selected Data Owners in order to manage the visibility over their assets, i.e. their data generated by devices under their control. The description of the devices and their usage in the pilot is given in the section PILOT.



# REPOSITORY STRUCTURE

The repository structure is organized in such a way to map the folders to the different elements of the architecture. The repository contains the following folders: 

- common: collects modules shared between multiple classes in the project, and between the different components 

- components: contains the different components of the Data Ownership Orchestration Framework in specific subfolders: DOOF Clients, DOOF Gateway, DOOF worker, intermediation (smart contract)

- conf: contains some configuration utils for the deployment of the software 

- configuration_tool: contains a micropython web server deployed on the end-user's devices (data origins) to make the configuration of the connectivity and of other aspects of the data origin easier. 

- documentation: it contains the architectural diagram of the system 

- installation: it contains documents, scripts, and requirements regarding the installation procedure of DOOF components and their dependencies. 

- pilot: this folder contains the source code of the front-end that was developed during the pilot for usage by the participants in the user-centric research phase of the project

- provider: contains the different providers (modules) that can be loaded at run time by the different components. The input and output providers represented in the architecture schemas are found under the 'presentation' subfolder, the persistence provider that communicates with a database is found under the 'persistence' subfolder and the provider that communicates with the intermediation platform/smart contract is found under 'intermediation' subfolder. Moreover, the 'processors' subfolder contains the processors that populate the worker's pipeline and allow to deliver the business logic functionality of consent management and facilitation of deployment of Privacy Enhancing Technologies.
 

The following sections will present each of the components into greater detail. 


## DOOF Client
The DOOF Client is a front-end component. DOOF clients offer APIs for the exploitation of all the back-end capabilities. These APIs can be integrated into different kind of applications, such as web applications, desktop applications or command line applications.

The client communicates with the DOOF Gateway via Client/Server transport protocol such as HTTPS. The client receives events - asynchronous notifications from the worker - via a pub/sub broker such as MQTT broker. 


## DOOF Gateway 
The DOOF Gateway is a web server application that can be hosted on an HTTP server. It offers to clients a set of RESTful web services to facilitate the way in which they consume the DOOF backend services. Through the APIs exposed by the Web Services, the DOOF clients can send events to the Work Queue, i.e. a server implemeneting AMQP protocol. The Work Queue allows the implementation of a competing consumers pattern, which enhances the scalability and availability of the back-end worker's. 

## DOOF Worker
The DOOF Worker is the main component of the ecosystem. It implements an Orchestration Framework tailored with Data Ownership capabilities. 
The orchestration framework coordinates, manages and monitors different tasks and services. These services vary from infrastructural services, such as connectivity with third party components as persistence layers and blockchain systems, to microtasks execution and error handling. 

The DOOF worker processes incoming events - imperatives - by selecting a configurable pipeline of processors loaded dynamically. These processors implement the business logic necessary for the delivery of Data Ownership capabilities, by interacting, via specific resource managers, with the blockchain and the database.  




## Smart Contract
The smart contract written in Solidity exposes all the logic necessary to a data stream marketplace initiative. In this respect, every marketplace is associated to a single smart contract and each smart contract holds all the products populating the marketplace. A marketplace is an initiative that promotes the trading of data visibility amongst data owners (selling side) and data users (buying side). Both data owners and data users are represented as “members” within the smart contract.

The smart contract holds infomation about members, the participants to the initiative,  about products, i.e. representations of data sets/data origins, and about subscriptions, i.e. the interest expressed by data recipients of having visibility over a data set/data stream.

The smart contract offers a decentralized and verifiable repository holding data recipients interests in data visibility and data owners decisions alike. 


# PILOT 
The DOOF components and APIs are validated via the Data Exchange pilot, developed by integrating the input of our users and deployed in collaboration with our partners Sidera and Nexus-TLC. This Data Exchange Pilot offers selected data owners the access to the consent management capabilities of the DOOF, and a data origin integrated with a selected PET, the Ecosteer proprietary Data Visibility Control Overlay (DVCO). 

The selected data origins are Smart Home devices for Air Quality monitoring, named Qubees. The device generates a data stream that is encrypted via DVCO protocol, a data stream that is represented on the web data exchange via a product. Data users/recipients will be able to decrypt this data only if explicitly granted by the data owner.

The data owner to which this product belongs can grant and revoke data visibility of third parties over this data stream at any time, for any reason. 

The pilot was validated by the participants to the user-centric research, whose feedback was valuable into finding and implementing improvements in the user interface and functionality delivery. 

# Installation and deployment 
For the installation of the components and their dependencies please follow the steps documented in 1-DOOF_dependencies_and_third-party_installation and then in 2.DOOF-components-configuraiton under installation folder.
